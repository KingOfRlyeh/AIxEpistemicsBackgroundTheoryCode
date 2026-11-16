"""Writes scored_32.jsonl: every graded run from the main run except the one dropped item.

The item conflict_W3023274331_W2021991108 was generated without an orphan statement and its
Q2 conclusion is accepted by both frameworks, so the paper excludes it (32 conflict items remain).

Usage (from analysis/main_run/):  python exclude_dropped_item.py
"""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "pair-finder", "results", "run2", "scored_all.jsonl")
DROPPED = "W3023274331_W2021991108"
kept = [l for l in open(SRC, encoding="utf-8") if l.strip() and DROPPED not in l]
open(os.path.join(HERE, "scored_32.jsonl"), "w", encoding="utf-8").writelines(kept)
print(f"wrote scored_32.jsonl: {len(kept)} runs")
