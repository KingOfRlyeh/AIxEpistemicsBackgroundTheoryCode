"""Minimal OpenAlex client: search works per framework side, fetch by DOI."""
import os
import time

import requests

BASE = "https://api.openalex.org"
FIELDS = "id,doi,title,publication_year,cited_by_count,abstract_inverted_index,authorships,primary_topic"


def _params(extra):
    p = dict(extra)
    if os.environ.get("OPENALEX_API_KEY"):
        p["api_key"] = os.environ["OPENALEX_API_KEY"]
    if os.environ.get("OPENALEX_MAILTO"):
        p["mailto"] = os.environ["OPENALEX_MAILTO"]
    return p


def _get(path, params, retries=5):
    for i in range(retries):
        r = requests.get(BASE + path, params=_params(params), timeout=30)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 ** i)
            continue
        if r.status_code != 200:
            raise RuntimeError(f"OpenAlex {r.status_code}: {r.text[:300]}")
        return r.json()
    raise RuntimeError(f"OpenAlex failed after {retries} retries: {path}")


def abstract_from_index(inv):
    if not inv:
        return ""
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos))


def to_record(w):
    return {
        "openalex_id": w["id"].rsplit("/", 1)[-1],
        "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
        "title": w.get("title") or "",
        "year": w.get("publication_year"),
        "cited_by_count": w.get("cited_by_count", 0),
        "authors": [a["author"]["display_name"] for a in (w.get("authorships") or [])[:6]],
        "topic": ((w.get("primary_topic") or {}).get("display_name")) or "",
        "abstract": abstract_from_index(w.get("abstract_inverted_index")),
    }


def search(query, n=20, min_citations=10, extra_filter="", pool=25):
    """Most-relevant `pool` works for a query, then the `n` most cited of those.

    Sorting by citations directly lets loosely matching blockbuster papers in;
    relevance first keeps results on topic. `extra_filter` is an OpenAlex filter
    string, e.g. "primary_topic.field.id:20" (Economics, Econometrics and Finance).
    """
    filt = f"has_abstract:true,cited_by_count:>{min_citations},type:article|review"
    if extra_filter:
        filt += "," + extra_filter
    data = _get("/works", {"search": query, "filter": filt, "per-page": min(max(pool, n), 200), "select": FIELDS})
    recs = [to_record(w) for w in data.get("results", [])]
    recs.sort(key=lambda r: -r["cited_by_count"])
    return recs[:n]


def by_doi(doi):
    w = _get(f"/works/doi:{doi}", {"select": FIELDS})
    return to_record(w)
