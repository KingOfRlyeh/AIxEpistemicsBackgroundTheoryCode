# Hidden Theoretical Conflict in Citations

Code, data and analysis for "Hidden Theoretical Conflict in Citations: LLM Syntheses Merge Findings from Rival Frameworks Without Flagging Them" (AI x Epistemics Research Sprint, Apart Research, November 2026). The paper text is in `paper/paper.md`.

## Layout

| Path | Contents |
|---|---|
| `pair-finder/` | Pipeline that builds rival-framework items from OpenAlex papers, runs the evaluation, and grades it. See `pair-finder/README.md` and `pair-finder/REPRODUCE.md`. |
| `pair-finder/frameworks.yaml` | Rival-framework catalogue (macroeconomics, cosmology). |
| `pair-finder/eval/run2/` | Run 2 items, prompts, model runs and grades. |
| `pair-finder/results/run2/scored_all.jsonl` | All graded run 2 runs (input to the analysis). |
| `pair-finder/results/run2/regrade_gemma/` | Second-grader (gemma-4-31b-it) regrade, pass 2. |
| `analysis/run2/` | Item-level analysis scripts, second-grader script and pass-1 regrade, and `run2_browser.html` for reading every graded run. |
| `analysis/run2_v4/` | Tables and Figure 1 as reported in the paper (monetary-policy item `conflict_W3023274331_W2021991108` excluded; see paper, Methods). |
| `pretest/` | Hand-built pre-test: every prompt and response (`results.jsonl`), hand codes, scoring script, Figure 2, and `pretest_browser.html`. |

## Reproducing the paper's numbers

```
grep -v W3023274331_W2021991108 pair-finder/results/run2/scored_all.jsonl > /tmp/scored.jsonl
cd analysis/run2_v4 && python ../run2/analyze.py /tmp/scored.jsonl && python ../run2/make_figure.py /tmp/scored.jsonl
cd ../../pretest && python score_and_report_v4.py
```

Model calls need API keys (see `pair-finder/REPRODUCE.md`); the analysis scripts above need only Python 3 and matplotlib.

Items, verdicts and orphan statements were written by an LLM and were not checked by subject experts. All labels come from LLM graders.
