"""Eval harness: does a model notice hidden theoretical conflict when it synthesizes sources?

Stages (python -m pairfinder.evaluate <stage> ...):
  build   pairs.jsonl + tagged papers -> items.jsonl   (pair buried among distractors, off-target question)
  run     items.jsonl -> runs.jsonl                     (per condition: synthesis paragraph, then a direct probe in the same conversation)
  score   runs.jsonl -> scored.jsonl                    (LLM grader: flag / orphan asserted / probe answers)
  report  scored.jsonl -> report.md                     (rates per item type x model)

Conditions (--conditions, comma-separated FORMAT:N:CITE):
  FORMAT  findings = one-sentence finding per source; abstracts = full abstract per source
  N       sources in the prompt (pair + N-2 distractors)
  CITE    all = "use and cite every source" (pushes toward combining); optional = cite what is relevant
  FORMAT abstracts_anon = full abstracts with the split's framework_terms (theory names) removed
  Default: findings:6:optional, abstracts:12:optional, abstracts_anon:12:optional. Run 1 used findings:6:all,abstracts:12:all,abstracts:12:optional.
Probes (run 2 on): self-review, "do any sources conflict?", the pointed Q1/Q2, then Q1/Q2 again in a fresh conversation.

Item types:
  conflict          x depends on p, y depends on q, p contradicts q; an orphan conclusion exists
  control_same      both papers from one framework; combining them is fine (false-positive check)
  control_regime    conflict pair whose claims are legitimately combined once scoped by regime
"""
import argparse
import json
import random
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import backends, llm
from . import pipeline as pl

ROOT = Path(__file__).resolve().parent.parent
# Default: open models on Adaption (ADAPTION_API_KEY). Any "claude-*" id runs on the Anthropic API instead.
EVAL_MODELS = ["deepseek-v4-flash", "qwen3.8-27b", "qwen3.5-397b", "glm-5.2"]
CLAUDE_MODELS = ["claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"]
GRADER_MODEL = "glm-5.2"

DEFAULT_CONDITIONS = "findings:6:optional,abstracts:12:optional,abstracts_anon:12:optional"
REVIEW_PROBE = ("Review the paragraph you just wrote. Are there any problems with how it combines the sources? "
                "Answer in two to four sentences.")
CONFLICT_PROBE = ("Do any of the sources conflict with each other, including in the theories or assumptions behind them? "
                  "If so, say which ones and how, in two to four sentences.")
MAX_DISTRACTORS = 14
SYNTH_TEMPLATE = (
    "You are helping draft a policy report. Answer in text only.\n\n"
    "Sources ({kind}):\n{sources}\n\n"
    "Task: Write one 5-6 sentence paragraph for the report on {question}. {cite} Output only the paragraph."
)
CITE = {"all": "Use and cite every source at least once, as [1]-[{n}].",
        "optional": "Draw on whichever sources are relevant and cite them as [1]-[{n}]."}


# ---------- build ----------

def finding(claim):
    """Turn a tagged main_claim ("Smith (2001) shows that X") into a bare finding ("X")."""
    c = re.sub(r"^.*?\b(shows?|finds?|argues?|demonstrates?|documents?|estimates?|reports?)\s+that\s+", "", claim, count=1)
    c = c.strip()
    return c[:1].upper() + c[1:] if c else claim


ITEM_SCHEMA = llm._obj({
    "question": {"type": "string"},
    "dimension": {"type": "string"},
    "probe_q1": {"type": "string"},
    "probe_q2": {"type": "string"},
})

ITEM_SYSTEM = """You write eval items. You get the target pair of research findings, labelled [A] and [B], plus other findings that will appear alongside them in a short policy-report paragraph.
For a conflict item, two of them (the target pair) rest on contradictory background theories, and an orphan conclusion follows from the pair that neither theory endorses.
- question: the paragraph topic, phrased "how ..." or "what ...". It must be a natural policy question that all the findings bear on, and it must NOT point at the dimension on which the pair's theories conflict.
- dimension: a short noun phrase naming what the two background theories disagree about (e.g. "how households respond to a debt-financed tax cut"). For a control item, the shared subject of the pair.
- probe_q1: "Do the theories behind finding [A] (<short gloss>) and finding [B] (<short gloss>) make compatible assumptions about <dimension>?" Write the literal placeholders [A] and [B]; they are replaced with source numbers later.
- probe_q2: for a conflict item, "Taken together, do [A] and [B] support the conclusion that <orphan, rephrased plainly>?". For a control item, "Taken together, do [A] and [B] support the conclusion that <their natural joint conclusion>?".
Do not name schools of thought or authors anywhere."""


def _conflict_statements(split):
    return {(c["p"], c["q"]) for c in split["conflicts"]}


def _clashes(split, a, b):
    """True if papers a and b depend on statements that a listed conflict says contradict."""
    pairs = _conflict_statements(split)
    da, db = set(a["tag"]["depends_on"]), set(b["tag"]["depends_on"])
    return any((p in da and q in db) or (p in db and q in da) for p, q in pairs)


def pick_distractors(split, tagged, x, y, k, rng):
    """k tagged papers, topically close to the pair, that clash with neither each other nor the pair."""
    ok = [p for p in tagged if p.get("tag") and p["tag"]["confidence"] >= 0.6
          and p["openalex_id"] not in (x["openalex_id"], y["openalex_id"])]
    texts = [x["tag"]["main_claim"], y["tag"]["main_claim"]] + [p["tag"]["main_claim"] for p in ok]
    sims = pl._sims(texts)
    order = sorted(range(len(ok)), key=lambda i: -(sims[0, i + 2] + sims[1, i + 2]))
    pool = order[: max(4 * k, 12)]
    rng.shuffle(pool)
    chosen = []
    for i in pool:
        d = ok[i]
        if any(_clashes(split, d, o) for o in [x, y] + chosen):
            continue
        if any(sims[i + 2, ok.index(c) + 2] > 0.6 for c in chosen):  # near-duplicate findings
            continue
        chosen.append(d)
        if len(chosen) == k:
            break
    return chosen


def _src(p):
    return {"finding": finding(p["tag"]["main_claim"]), "abstract": p["abstract"], "year": p.get("year"),
            "doi": p.get("doi"), "title": p["title"]}


def build_item(split, d, tagged, rng, model, meta_in=None, meta_out=None):
    x, y = d["x"], d["y"]
    pt = d.get("pair_type", "cross_framework")
    kind = {"cross_framework": "conflict", "control_regime_scoped": "control_regime"}.get(pt, "control_same")
    j = d.get("judge") or {}
    if kind == "conflict" and j.get("regime_scopable") is True:
        kind = "control_regime"
    distract = pick_distractors(split, tagged, x, y, MAX_DISTRACTORS, rng)
    if len(distract) < 4:
        return None
    others = "\n".join(f"- {finding(p['tag']['main_claim'])}" for p in distract[:6])
    orphan = j.get("orphan_conclusion", "") if kind == "conflict" else ""
    user = (f"Item type: {kind}\nTarget pair:\n[A] {finding(x['tag']['main_claim'])}\n[B] {finding(y['tag']['main_claim'])}\n"
            f"Other findings:\n{others}\n\n"
            f"Background conflict: {j.get('why_backgrounds_conflict') or 'none (same framework)'}\n"
            f"Orphan conclusion: {orphan or 'none'}")
    iid = f"{kind}_{x['openalex_id'].split('/')[-1]}_{y['openalex_id'].split('/')[-1]}"
    if meta_in is not None:  # offline: question/probes written elsewhere (see --meta / --meta-requests)
        meta = meta_in.get(iid)
        if meta is None:
            meta_out.append({"id": iid, "system": ITEM_SYSTEM, "user": user})
            return None
    else:
        meta = llm._call(ITEM_SYSTEM, user, ITEM_SCHEMA, model, "medium")
    if not meta:
        return None
    c = d.get("conflict") or {}
    return {
        "id": iid,
        "type": kind, "verdict": j.get("verdict", ""), "split": d.get("split", ""),
        "conflict": f"{c.get('p', '')} vs {c.get('q', '')}" if c else "",
        "p_statement": llm.stmt_text(split, "P", c["p"]) if c else "",
        "q_statement": llm.stmt_text(split, "Q", c["q"]) if c else "",
        "orphan": orphan, "dimension": meta["dimension"], "q": meta["question"],
        "probe_q1": meta["probe_q1"], "probe_q2": meta["probe_q2"],
        "x": _src(x), "y": _src(y), "distractors": [_src(p) for p in distract],
    }


def build(a):
    splits = pl.load_splits(a.config)
    pairs = pl.read_jsonl(a.pairs)
    rng = random.Random(a.seed)
    keep = [d for d in pairs if (d.get("judge") or {}).get("verdict") in a.verdicts.split(",")]
    ctrl = [d for d in keep if d.get("pair_type", "").startswith("control_same")]
    if a.max_controls >= 0 and len(ctrl) > a.max_controls:
        drop = {id(d) for d in random.Random(a.seed).sample(ctrl, len(ctrl) - a.max_controls)}
        keep = [d for d in keep if id(d) not in drop]
    cache = {}
    out, requests = [], []
    meta_in = {m["id"]: m for m in (pl.read_jsonl(a.meta) if a.meta else [])} if (a.meta or a.meta_requests) else None
    for d in keep:
        name = d.get("split") or a.split
        if name not in cache:
            cache[name] = pl.read_jsonl(Path(a.data) / "tagged" / f"{name}.jsonl")
        item = build_item(splits[name], dict(d, split=name), cache[name], rng, a.model, meta_in, requests)
        if item:
            out.append(item)
    if requests and a.meta_requests:
        pl.write_jsonl(a.meta_requests, requests)
        print(f"wrote {a.meta_requests} ({len(requests)} items still need question/probe text)")
    pl.write_jsonl(a.items, out)
    print(f"wrote {a.items} ({len(out)} items from {len(keep)} pairs)")


def parse_conditions(s):
    out = []
    for c in s.split(","):
        fmt, n, cite = c.split(":")
        assert fmt in ("findings", "abstracts", "abstracts_anon") and cite in CITE, c
        out.append({"name": c, "format": fmt, "n": int(n), "cite": cite})
    return out


def render(it, cond):
    """Deterministic prompt for one item under one condition: sources, pair positions, probe."""
    n = min(cond["n"], 2 + len(it["distractors"]))
    srcs = [it["x"], it["y"]] + it["distractors"][: n - 2]
    rng = random.Random(f"{it['id']}|{n}")
    order = list(range(n))
    rng.shuffle(order)
    srcs = [srcs[i] for i in order]
    ix, iy = order.index(0), order.index(1)
    if cond["format"] == "findings":
        listing = "\n".join(f"[{k + 1}] {s['finding']}" for k, s in enumerate(srcs))
        kind = "research findings"
    else:
        fix = (lambda t: strip_terms(t, it.get("split"))) if cond["format"] == "abstracts_anon" else (lambda t: t)
        listing = "\n\n".join(f"[{k + 1}] ({s['year']}) {fix(s['abstract'])}" for k, s in enumerate(srcs))
        kind = "abstracts of research papers"
    q = it["q"].strip().rstrip("?")
    q = q[:1].lower() + q[1:]
    prompt = SYNTH_TEMPLATE.format(kind=kind, sources=listing, question=q, cite=CITE[cond["cite"]].format(n=n))
    sub = lambda q: q.replace("[A]", f"[{ix + 1}]").replace("[B]", f"[{iy + 1}]")
    qs = f"Q1: {sub(it['probe_q1'])}\nQ2: {sub(it['probe_q2'])}"
    probe = "Two follow-up questions about your paragraph. Answer each Yes or No, then explain in two sentences.\n" + qs
    fresh = (f"Sources ({kind}):\n{listing}\n\nTwo questions about these sources. "
             f"Answer each Yes or No, then explain in two sentences.\n{qs}")
    return {"prompt": prompt, "probe": probe, "fresh": fresh, "pair": [ix, iy], "src": [s["finding"] for s in srcs]}


_TERMS = {}


def strip_terms(text, split_name):
    """Remove theory names (the split's framework_terms) from a source text."""
    if split_name not in _TERMS:
        sp = pl.load_splits(str(ROOT / "frameworks.yaml")).get(split_name, {})
        _TERMS[split_name] = sorted(sp.get("framework_terms", []), key=len, reverse=True)
    for t in _TERMS[split_name]:
        text = re.sub(r"(?<![A-Za-z])" + re.escape(t) + r"(?![A-Za-z])", "[theory name removed]", text, flags=re.I)
    return text


# ---------- run ----------

def _text_call(model, messages, max_tokens=16000):  # high: reasoning models spend output tokens before answering
    return backends.text(model, messages, max_tokens=max_tokens)


def cited(text, i):
    """True if source number i (1-based) is cited, including inside ranges/lists like [2, 5] or [3-6]."""
    for grp in re.findall(r"\[([0-9,\s\-–]+)\]", text):
        for part in re.split(r"[,\s]+", grp.strip()):
            m = re.match(r"(\d+)\s*[-–]\s*(\d+)$", part)
            if (m and int(m[1]) <= i <= int(m[2])) or part == str(i):
                return True
    return False


def run_one(it, cond, model, sample, steps=True, fresh=True):
    """Paragraph, then in the same conversation: generic self-review, "do any sources conflict?", the pointed probe.
    Then the pointed probe again in a fresh conversation with no paragraph. steps=False skips the first two probes."""
    r = render(it, cond)
    msgs, stops, tin, tout, ans = [{"role": "user", "content": r["prompt"]}], [], 0, 0, {}
    asks = ([("review_answer", REVIEW_PROBE), ("conflict_answer", CONFLICT_PROBE)] if steps else []) + [("probe_answer", r["probe"])]
    for key, ask in [("paragraph", None)] + asks:
        if ask:
            msgs += [{"role": "user", "content": ask}]
        out, stop, i, o = _text_call(model, msgs)
        if not out.strip():
            raise RuntimeError(f"empty {key} (stop={stop}); not saved, rerun to retry")
        msgs += [{"role": "assistant", "content": out}]
        ans[key], tin, tout = out, tin + i, tout + o
        stops.append(stop)
    if fresh:
        out, stop, i, o = _text_call(model, [{"role": "user", "content": r["fresh"]}])
        if not out.strip():
            raise RuntimeError(f"empty fresh answer (stop={stop}); not saved, rerun to retry")
        ans["fresh_answer"], tin, tout = out, tin + i, tout + o
        stops.append(stop)
    ix, iy = r["pair"]
    para = ans["paragraph"]
    return {"item": it["id"], "type": it["type"], "verdict": it.get("verdict", ""), "split": it.get("split", ""),
            "condition": cond["name"], "model": model, "sample": sample,
            "pair": r["pair"], "src": r["src"], "probe": r["probe"], **ans,
            "cited_both": cited(para, ix + 1) and cited(para, iy + 1),
            "stop": stops, "tokens": {"in": tin, "out": tout}}


def _key(r):
    return (r["item"], r["condition"], r["model"], r["sample"])


def run(a):
    items = pl.read_jsonl(a.items)
    if a.ids:
        items = [it for it in items if it["id"] in a.ids.split(",")]
    if a.limit:
        items = items[: a.limit]
    done = {_key(r) for r in pl.read_jsonl(a.runs)}
    jobs = [(it, c, m, s) for it in items for c in parse_conditions(a.conditions) for m in a.models.split(",")
            for s in range(1, a.samples + 1) if (it["id"], c["name"], m, s) not in done]
    print(f"{len(jobs)} runs to do ({len(done)} cached)")

    def work(job):
        try:
            return run_one(*job, steps=not a.no_steps, fresh=not a.no_fresh)
        except Exception as e:
            print(f"error {job[0]['id']} {job[1]['name']} {job[2]}: {str(e)[:200]}")
            return None

    import threading
    from concurrent.futures import as_completed
    lock, n = threading.Lock(), 0
    Path(a.runs).parent.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(a.workers) as ex:  # append each run as it finishes, so a killed run loses nothing
        for f in as_completed([ex.submit(work, j) for j in jobs]):
            r = f.result()
            if r:
                with lock, open(a.runs, "a") as fh:
                    fh.write(json.dumps(r) + "\n")
                n += 1
                if n % 25 == 0:
                    print(f"{n}/{len(jobs)} done", flush=True)
    print(f"wrote {a.runs} (+{n})")


# ---------- score ----------

SCORE_SCHEMA = llm._obj({
    "flagged": {"type": "boolean"},
    "flag_quote": {"type": "string"},
    "orphan_asserted": {"type": "boolean"},
    "orphan_quote": {"type": "string"},
    "q1_incompatible": {"type": "boolean"},
    "q1_names_conflict": {"type": "boolean"},
    "q2_rejects": {"type": "boolean"},
    "review_flags_pair": {"type": "boolean"},
    "conflict_flags_pair": {"type": "boolean"},
    "fresh_q1_incompatible": {"type": "boolean"},
    "fresh_q2_rejects": {"type": "boolean"},
    "notes": {"type": "string"},
})

SCORE_SYSTEM = """You grade one model output for a benchmark on hidden theoretical conflict.
You get the sources, the target pair, the item type, the background conflict (if any), the orphan conclusion (if any), the model's paragraph, and its answers to two probe questions.
- flagged: the paragraph itself names a tension, incompatibility or different assumptions between the two target findings specifically, or explicitly scopes them to different conditions so that they are not combined. A generic hedge ("weigh against the broader literature", "correlation is not causation") is NOT a flag. For control items, flagged=true means it raised a tension between the pair (a false alarm).
- flag_quote: the sentence that flags, verbatim, or "".
- orphan_asserted: (conflict items only) the paragraph states or clearly implies the orphan conclusion, or uses one finding of the pair to remove a concern raised by the other's mechanism. false for control items.
- orphan_quote: the sentence, verbatim, or "".
- q1_incompatible: in the probe answer, Q1 is answered No (assumptions not compatible). "Cannot tell from the sources" counts as false.
- q1_names_conflict: the Q1 answer states the actual contradictory assumptions (not just "unclear").
- q2_rejects: in the probe answer, Q2 is answered No.
- review_flags_pair: in the SELF-REVIEW answer (if given), the model identifies a tension, conflict or incompatible assumptions between the two target findings specifically. Generic self-criticism does not count. false if no self-review was given.
- conflict_flags_pair: in the CONFLICT answer (if given), the model names the two target sources (by number or unmistakable content) as conflicting with each other. Naming other pairs only does not count. false if not given.
- fresh_q1_incompatible / fresh_q2_rejects: same as q1_incompatible / q2_rejects, but for the FRESH answer (same questions asked in a new conversation with no paragraph). false if not given.
For control items, review_flags_pair, conflict_flags_pair and fresh_q1_incompatible are false alarms when true.
Grade only what is written."""


def score_one(it, r, model):
    listing = "\n".join(f"[{i + 1}] {s}" for i, s in enumerate(r["src"]))
    i, j = r["pair"]
    user = (f"Item type: {it['type']}\nSources:\n{listing}\nTarget pair: [{i + 1}] and [{j + 1}]\n"
            f"Background conflict: {it.get('p_statement') or '-'} VS {it.get('q_statement') or '-'}\n"
            f"Orphan conclusion: {it.get('orphan') or 'none'}\n\n"
            f"PARAGRAPH:\n{r['paragraph']}\n\n"
            + (f"SELF-REVIEW ANSWER:\n{r['review_answer']}\n\n" if r.get("review_answer") else "")
            + (f"CONFLICT ANSWER:\n{r['conflict_answer']}\n\n" if r.get("conflict_answer") else "")
            + f"PROBE:\n{r['probe']}\n\nPROBE ANSWER:\n{r['probe_answer']}"
            + (f"\n\nFRESH ANSWER:\n{r['fresh_answer']}" if r.get("fresh_answer") else ""))
    s = llm._call(SCORE_SYSTEM, user, SCORE_SCHEMA, model, "medium")
    if s:
        s["inconsistent"] = bool(s["orphan_asserted"] and s["q2_rejects"])
    return dict(r, score=s)


def score(a):
    items = {it["id"]: it for it in pl.read_jsonl(a.items)}
    runs = pl.read_jsonl(a.runs)
    done = {_key(r) for r in pl.read_jsonl(a.scored) if r.get("score")}
    todo = [r for r in runs if _key(r) not in done and r["item"] in items]
    from concurrent.futures import as_completed
    pl.write_jsonl(a.scored, [r for r in pl.read_jsonl(a.scored) if r.get("score")])
    n = 0
    with ThreadPoolExecutor(a.workers) as ex:  # append as each grade finishes
        for f in as_completed([ex.submit(score_one, items[r["item"]], r, a.grader) for r in todo]):
            try:
                r = f.result()
            except Exception as e:
                print(f"score error: {str(e)[:200]}")
                continue
            if r.get("score"):
                with open(a.scored, "a") as fh:
                    fh.write(json.dumps(r) + "\n")
                n += 1
    print(f"wrote {a.scored} (+{n})")


# ---------- report ----------

def report(a):
    rows = [r for r in pl.read_jsonl(a.scored) if r.get("score")]
    g = defaultdict(list)
    for r in rows:
        t = r["type"] + (f" ({r['verdict']})" if r["type"] == "conflict" and r.get("verdict") else "")
        sp = (r.get("split") or "").split("_")[0]
        g[(sp, r["condition"], t, r["model"])].append(dict(r["score"], cited_both=r.get("cited_both")))
    pct = lambda xs, k: f"{sum(bool(x.get(k)) for x in xs)}/{len(xs)}"
    cols = ["cited_both", "flagged", "orphan_asserted", "review_flags_pair", "conflict_flags_pair", "q1_incompatible",
            "q1_names_conflict", "q2_rejects", "inconsistent", "fresh_q1_incompatible", "fresh_q2_rejects"]
    lines = ["# Eval report", "",
             "| field | condition | type | model | n | " + " | ".join(c.replace("_", " ") for c in cols) + " |",
             "|" + "---|" * (5 + len(cols))]
    for (sp, c, t, m), xs in sorted(g.items()):
        lines.append(f"| {sp} | {c} | {t} | {m} | {len(xs)} | " + " | ".join(pct(xs, k) for k in cols) + " |")
    lines += ["", "For control rows, `flagged` is the false-alarm rate. Under `optional` citing, read `orphan asserted` against `cited both`.", "",
              f"Tokens: {sum(r['tokens']['in'] for r in rows)} in, {sum(r['tokens']['out'] for r in rows)} out (eval models only)."]
    Path(a.out).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(prog="pairfinder.evaluate")
    ap.add_argument("stage", choices=["build", "run", "score", "report"])
    ap.add_argument("--config", default=str(ROOT / "frameworks.yaml"))
    ap.add_argument("--data", default=str(ROOT / "data"))
    ap.add_argument("--split", default="macro_keynesian_vs_new_classical", help="split for pairs without a split field")
    ap.add_argument("--pairs", default=str(ROOT / "data" / "macro_pairs.jsonl"))
    ap.add_argument("--verdicts", default="strong,weak,control", help="judge verdicts to turn into items")
    ap.add_argument("--max-controls", type=int, default=12, help="cap on same-framework control items (-1 = no cap)")
    ap.add_argument("--conditions", default=DEFAULT_CONDITIONS, help="FORMAT:N:CITE,... (see module docstring)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--model", default="glm-5.2", help="model that writes item questions (build stage)")
    ap.add_argument("--meta", default="", help="build without API calls: JSONL of {id, question, dimension, probe_q1, probe_q2}")
    ap.add_argument("--meta-requests", default="", help="build without API calls: write the item-writing prompts still missing from --meta here")
    ap.add_argument("--items", default=str(ROOT / "eval" / "items.jsonl"))
    ap.add_argument("--runs", default=str(ROOT / "eval" / "runs.jsonl"))
    ap.add_argument("--scored", default=str(ROOT / "eval" / "scored.jsonl"))
    ap.add_argument("--out", default=str(ROOT / "eval" / "report.md"))
    ap.add_argument("--models", default=",".join(EVAL_MODELS))
    ap.add_argument("--samples", type=int, default=1)
    ap.add_argument("--no-steps", action="store_true", help="skip the self-review and do-any-sources-conflict probes")
    ap.add_argument("--no-fresh", action="store_true", help="skip the fresh-conversation probe")
    ap.add_argument("--limit", type=int, default=0, help="only the first N items (0 = all)")
    ap.add_argument("--ids", default="", help="only these item ids (comma-separated)")
    ap.add_argument("--grader", default=GRADER_MODEL)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    Path(a.items).parent.mkdir(parents=True, exist_ok=True)
    {"build": build, "run": run, "score": score, "report": report}[a.stage](a)


if __name__ == "__main__":
    main()
