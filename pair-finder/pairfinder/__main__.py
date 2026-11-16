"""CLI. Run `python -m pairfinder --help`."""
import argparse
from pathlib import Path

from . import pipeline as pl
from .llm import DEFAULT_MODEL

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser(prog="pairfinder")
    ap.add_argument("stage", choices=["list", "fetch", "tag", "pair", "run"])
    ap.add_argument("--splits", default="all", help="comma-separated split names, or 'all'")
    ap.add_argument("--config", default=str(ROOT / "frameworks.yaml"))
    ap.add_argument("--data", default=str(ROOT / "data"))
    ap.add_argument("--per-query", type=int, default=10, help="OpenAlex results per search query")
    ap.add_argument("--min-citations", type=int, default=10)
    ap.add_argument("--model", default="glm-5.2", help="glm-5.2 etc. run on Adaption; claude-* ids on the Anthropic API")
    ap.add_argument("--top-k", type=int, default=6, help="pairs kept per split")
    ap.add_argument("--min-conf", type=float, default=0.6)
    ap.add_argument("--controls", type=int, default=4, help="same-framework control pairs per split")
    ap.add_argument("--no-judge", action="store_true", help="skip the per-pair LLM judge")
    ap.add_argument("--no-llm", action="store_true", help="skip all LLM calls; rank raw cross-side pairs by text similarity")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()

    splits = pl.load_splits(a.config)
    names = list(splits) if a.splits == "all" else a.splits.split(",")
    data = Path(a.data)

    if a.stage == "list":
        for n in names:
            s = splits[n]
            print(f"{n}: {s['P']['name']}  vs  {s['Q']['name']}  ({len(s['conflicts'])} conflicts)")
        return

    all_rows, all_pairs = [], []
    for n in names:
        s = splits[n]
        pfile, tfile = data / "papers" / f"{n}.jsonl", data / "tagged" / f"{n}.jsonl"

        if a.stage in ("fetch", "run") or not pfile.exists():
            papers = pl.fetch_split(s, a.per_query, a.min_citations)
            pl.write_jsonl(pfile, papers)
            print(f"[{n}] fetched {len(papers)} papers")
        papers = pl.read_jsonl(pfile)
        if a.stage == "fetch":
            continue

        if a.no_llm:
            pairs = pl.raw_pairs(s, papers, top_k=a.top_k)
        else:
            if a.stage in ("tag", "run") or not tfile.exists():
                tagged = pl.tag_split(s, papers, a.model, a.workers, existing=pl.read_jsonl(tfile))
                pl.write_jsonl(tfile, tagged)
                print(f"[{n}] tagged {sum(1 for p in tagged if p.get('tag'))}/{len(tagged)}")
            tagged = pl.read_jsonl(tfile)
            if a.stage == "tag":
                continue
            pairs = pl.candidate_pairs(s, tagged, min_conf=a.min_conf, top_k=a.top_k)
            pairs += pl.same_framework_controls(s, tagged, min_conf=a.min_conf, top_k=a.controls)
            if not a.no_judge:
                pairs = pl.judge(s, pairs, a.model, a.workers)
        print(f"[{n}] {len(pairs)} candidate pairs")
        all_pairs += [dict(p, split=n) for p in pairs]
        all_rows += [pl.flatten(n, s, p) for p in pairs]

    if all_rows:
        stem = "raw_pairs" if a.no_llm else "pairs"
        pl.write_jsonl(data / f"{stem}.jsonl", all_pairs)
        pl.write_csv(data / f"{stem}.csv", all_rows)
        print(f"wrote {data / (stem + '.csv')} ({len(all_rows)} rows)")


if __name__ == "__main__":
    main()
