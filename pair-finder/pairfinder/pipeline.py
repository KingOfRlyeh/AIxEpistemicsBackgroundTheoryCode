"""Stages: fetch -> tag -> pair (+ judge) -> export."""
import csv
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from . import llm, openalex


def load_splits(path):
    return yaml.safe_load(Path(path).read_text())["splits"]


def read_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


# ---------- fetch ----------

def fetch_split(split, per_query=15, min_citations=10):
    seen, titles, out, both = {}, set(), [], set()
    for side in ("P", "Q"):
        fw = split[side]
        recs = []
        for q in fw.get("queries", []):
            recs += openalex.search(q, n=per_query, min_citations=min_citations,
                                    extra_filter=split.get("openalex_filter", ""))
        for doi in fw.get("seed_dois", []) or []:
            recs.append(openalex.by_doi(doi))
        for r in recs:
            key = r["openalex_id"]
            if key in seen:
                if seen[key] != side:
                    both.add(key)
                continue
            tkey = r["title"].lower().strip()
            if tkey in titles:  # same paper indexed twice (e.g. working paper + article)
                continue
            titles.add(tkey)
            seen[key] = side
            r["side"] = side
            r["query_framework"] = fw["name"]
            out.append(r)
    # A paper retrieved by both sides' queries is ambiguous; drop it.
    return [r for r in out if r["openalex_id"] not in both and len(r["abstract"]) > 200]


# ---------- tag ----------

def tag_split(split, papers, model, workers=8, existing=None):
    done = {p["openalex_id"]: p for p in (existing or []) if p.get("tag")}
    todo = [p for p in papers if p["openalex_id"] not in done]

    def work(p):
        try:
            p = dict(p, tag=llm.tag_paper(split, p, model=model))
        except Exception as e:  # keep going; record the failure
            p = dict(p, tag=None, tag_error=str(e)[:300])
        return p

    with ThreadPoolExecutor(workers) as ex:
        new = list(ex.map(work, todo))
    return list(done.values()) + new


# ---------- pair ----------

def _sims(texts):
    if len(texts) < 2:
        return None
    m = TfidfVectorizer(stop_words="english", sublinear_tf=True).fit_transform(texts)
    return cosine_similarity(m)


def candidate_pairs(split, tagged, min_conf=0.6, top_k=6, max_per_paper=2, max_sim=0.85):
    """Cross-framework pairs where x depends on p, y on q, for a listed conflict (p, q)."""
    ok = [p for p in tagged if p.get("tag")]
    idx = {p["openalex_id"]: i for i, p in enumerate(ok)}
    sims = _sims([p["tag"]["main_claim"] for p in ok])
    cands = []
    for c in split["conflicts"]:
        xs = [p for p in ok if p["tag"]["side"] in ("P",) and c["p"] in p["tag"]["depends_on"] and p["tag"]["confidence"] >= min_conf]
        ys = [p for p in ok if p["tag"]["side"] in ("Q",) and c["q"] in p["tag"]["depends_on"] and p["tag"]["confidence"] >= min_conf]
        for x in xs:
            for y in ys:
                s = float(sims[idx[x["openalex_id"]], idx[y["openalex_id"]]]) if sims is not None else 0.0
                if s > max_sim:  # near-identical claims = same conclusion, not a conjunction
                    continue
                neutral = (1 + 0.5 * x["tag"]["claim_reads_framework_neutral"]) * (1 + 0.5 * y["tag"]["claim_reads_framework_neutral"])
                score = x["tag"]["confidence"] * y["tag"]["confidence"] * neutral * (0.3 + s)
                cands.append({"conflict": c, "x": x, "y": y, "claim_similarity": round(s, 3), "score": round(score, 4)})
    cands.sort(key=lambda d: -d["score"])
    picked, use = [], {}
    for d in cands:
        a, b = d["x"]["openalex_id"], d["y"]["openalex_id"]
        if use.get(a, 0) >= max_per_paper or use.get(b, 0) >= max_per_paper:
            continue
        picked.append(d)
        use[a] = use.get(a, 0) + 1
        use[b] = use.get(b, 0) + 1
        if len(picked) >= top_k:
            break
    return picked


def judge(split, cands, model, workers=8):
    def work(d):
        try:
            if d.get("pair_type", "cross_framework") != "cross_framework":
                return dict(d, judge=llm.control_conjunction(split, d["x"], d["y"], model=model))
            return dict(d, judge=llm.judge_pair(split, d["conflict"], d["x"], d["y"], model=model))
        except Exception as e:
            return dict(d, judge=None, judge_error=str(e)[:300])
    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(work, cands))


def raw_pairs(split, papers, top_k=10, min_sim=0.05, max_sim=0.6):
    """No-LLM mode: cross-side pairs on a related topic but not the same claim, by abstract TF-IDF."""
    sims = _sims([p["title"] + ". " + p["abstract"] for p in papers])
    out = []
    for i, x in enumerate(papers):
        for j, y in enumerate(papers):
            if x["side"] == "P" and y["side"] == "Q" and min_sim <= sims[i, j] <= max_sim:
                out.append({"conflict": None, "x": x, "y": y, "claim_similarity": round(float(sims[i, j]), 3),
                            "score": round(float(sims[i, j]), 4)})
    out.sort(key=lambda d: -d["score"])
    return out[:top_k]


def same_framework_controls(split, tagged, min_conf=0.6, top_k=6, max_per_paper=1, max_sim=0.85):
    """Control pairs: both papers rest on statements of the SAME framework, so their conjunction is coherent."""
    ok = [p for p in tagged if p.get("tag") and p["tag"]["confidence"] >= min_conf and p["tag"]["depends_on"]]
    idx = {p["openalex_id"]: i for i, p in enumerate(ok)}
    sims = _sims([p["tag"]["main_claim"] for p in ok])
    cands = []
    for side in ("P", "Q"):
        ids = set(split[side]["statements"])
        mine = [p for p in ok if p["tag"]["side"] == side and set(p["tag"]["depends_on"]) <= ids]
        for a in range(len(mine)):
            for b in range(a + 1, len(mine)):
                x, y = mine[a], mine[b]
                sim = float(sims[idx[x["openalex_id"]], idx[y["openalex_id"]]])
                if sim > max_sim:
                    continue
                score = x["tag"]["confidence"] * y["tag"]["confidence"] * (0.3 + sim)
                cands.append({"conflict": None, "x": x, "y": y, "claim_similarity": round(sim, 3),
                              "score": round(score, 4), "pair_type": f"control_same_{side}"})
    cands.sort(key=lambda d: -d["score"])
    picked, use = [], {}
    for d in cands:
        a, b = d["x"]["openalex_id"], d["y"]["openalex_id"]
        if use.get(a, 0) >= max_per_paper or use.get(b, 0) >= max_per_paper:
            continue
        picked.append(d)
        use[a] = use.get(a, 0) + 1
        use[b] = use.get(b, 0) + 1
        if len(picked) >= top_k:
            break
    return picked


def anonymize(text, split):
    """Strip citations and framework labels so a model can't recognise a famous rivalry by name."""
    import re
    labels = iter("ABCDEFGH")
    text = re.sub(r"\[[^\]]*\]", lambda m: f"[{next(labels, 'X')}]", text)
    for term in sorted(split.get("framework_terms", []), key=len, reverse=True):
        text = re.sub(re.escape(term), "[framework]", text, flags=re.I)
    return text


# ---------- export ----------

CSV_COLS = ["split", "domain", "framework_P", "framework_Q", "p_id", "p_statement", "q_id", "q_statement",
            "x_title", "x_year", "x_doi", "x_claim", "x_evidence", "y_title", "y_year", "y_doi", "y_claim", "y_evidence",
            "p_sources", "q_sources", "pair_type", "conjunction", "conjunction_anon", "x_background", "y_background", "why_conflict",
            "orphan_conclusion", "regime_scopable", "llm_verdict",
            "surface_consistent", "claim_similarity", "score", "llm_notes",
            "human_verdict", "human_notes"]


def _conflict(split, c):
    return next((k for k in split["conflicts"] if k["p"] == c["p"] and k["q"] == c["q"]), {})


def flatten(name, split, d):
    c, x, y, j = d.get("conflict"), d["x"], d["y"], d.get("judge") or {}
    return {
        "split": name, "domain": split.get("domain", ""),
        "framework_P": split["P"]["name"], "framework_Q": split["Q"]["name"],
        "p_id": c["p"] if c else "", "p_statement": llm.stmt_text(split, "P", c["p"]) if c else "",
        "q_id": c["q"] if c else "", "q_statement": llm.stmt_text(split, "Q", c["q"]) if c else "",
        "x_title": x["title"], "x_year": x.get("year"), "x_doi": x.get("doi"),
        "x_claim": (x.get("tag") or {}).get("main_claim", ""),
        "x_evidence": d.get("x_evidence") or (x.get("tag") or {}).get("evidence_quote", ""),
        "y_evidence": d.get("y_evidence") or (y.get("tag") or {}).get("evidence_quote", ""),
        "y_title": y["title"], "y_year": y.get("year"), "y_doi": y.get("doi"),
        "y_claim": (y.get("tag") or {}).get("main_claim", ""),
        "p_sources": "; ".join(_conflict(split, c).get("p_sources", [])) if c else "",
        "q_sources": "; ".join(_conflict(split, c).get("q_sources", [])) if c else "",
        "pair_type": d.get("pair_type", "cross_framework"),
        "conjunction": j.get("conjunction", ""), "conjunction_anon": anonymize(j.get("conjunction", ""), split),
        "orphan_conclusion": j.get("orphan_conclusion", ""), "regime_scopable": j.get("regime_scopable", ""),
        "x_background": j.get("x_background_statement", ""),
        "y_background": j.get("y_background_statement", ""), "why_conflict": j.get("why_backgrounds_conflict", ""),
        "llm_verdict": j.get("verdict", ""), "surface_consistent": j.get("surface_consistent", ""),
        "claim_similarity": d.get("claim_similarity"), "score": d.get("score"), "llm_notes": j.get("notes", ""),
        "human_verdict": "", "human_notes": "",
    }


def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLS)
        w.writeheader()
        w.writerows(rows)
