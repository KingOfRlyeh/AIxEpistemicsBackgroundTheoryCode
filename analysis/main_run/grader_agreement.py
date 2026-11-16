"""Second-grader agreement as reported in the paper (Results "Robustness", Appendix D).

Compares the primary grader (qwen3.8-27b) with the second grader (gemma-4-31b-it) on conflict
paragraphs from the three main models, with the dropped item excluded. Prints both regrade passes.

Usage (from analysis/main_run/):  python grader_agreement.py
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
PASSES = [("pass 1", os.path.join(HERE, "regrade.jsonl")),
          ("pass 2", os.path.join(HERE, "..", "..", "pair-finder", "results", "run2", "regrade_gemma", "regrade.jsonl"))]
MAIN_MODELS = {"deepseek-v4-flash", "qwen3.5-397b", "qwen3.8-27b"}
DROPPED = "W3023274331_W2021991108"

def kappa(pairs):
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    pa = sum(a for a, _ in pairs) / n; pb = sum(b for _, b in pairs) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0

for name, path in PASSES:
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    rows = [r for r in rows if r["type"] == "conflict" and DROPPED not in r["key"]
            and r["key"].split("|")[2] in MAIN_MODELS]
    print(f"{name}: {len(rows)} conflict paragraphs")
    for k in ("flagged", "orphan_asserted"):
        pairs = [(bool(r["first"][k]), bool(r["second"][k])) for r in rows]
        both = sum(a and b for a, b in pairs); first = sum(a and not b for a, b in pairs)
        second = sum(b and not a for a, b in pairs)
        agree = sum(a == b for a, b in pairs) / len(pairs)
        print(f"  {k}: agree {agree:.0%}, kappa {kappa(pairs):.2f} | both yes {both}, primary only {first}, second only {second}")
