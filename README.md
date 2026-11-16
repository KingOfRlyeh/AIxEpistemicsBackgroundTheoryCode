# Hidden Theoretical Conflict in Citations: LLMs Rarely Disclose Rival Frameworks Unprompted

Code, data, and analysis for our submission to the AI x Epistemics Research Sprint (Apart Research, November 2026), Track 1: Model Epistemics & Decision-Making Evals.

Authors: Jack Bollenbacher and Angela Yue (Texas A&M University).

## What this is

An LLM asked to synthesize research can cite two sources that are each sound but rest on rival theories, for example Keynesian versus New Classical macroeconomics. We test two things:

1. **Disclosure.** Does the synthesis tell the reader that two of its sources come from rival frameworks, given that the model can identify the rivalry when asked?
2. **Orphan conclusions.** Does the synthesis assert a joint conclusion that neither theory supports, and that the same model rejects when asked separately?

## Headline results

Main run: 282 runs on 32 rival-framework source pairs, three open-weight models (deepseek-v4-flash, qwen3.5-397b, qwen3.8-27b).

| | Macroeconomics | Cosmology |
|---|---|---|
| Paragraph flags the rival pair unprompted | 9% | 22% |
| After a generic self-review | 14% | 33% |
| Asked about the pair directly | 96% | 92% |
| Same question, same-theory controls | 3% | 6% |
| Paragraph asserts the orphan conclusion | 3% | 15% |

Controlled experiment (one hand-built pair, four models): the orphan conclusion appeared in 19 of 20 briefs when sources were cut to one-line findings and in 0 of 20 when they kept their scope conditions. In separate fresh-conversation probes, no model endorsed it (0 of 24).

## Repository layout

| Path | Contents |
|---|---|
| `pair-finder/` | Experiment 1 pipeline: builds rival-framework items from OpenAlex papers, runs the synthesis task and probe ladder, and grades the runs. See `pair-finder/README.md` and `pair-finder/REPRODUCE.md`. |
| `pair-finder/frameworks.yaml` | Rival-framework catalog (core statements and the pairs that contradict). |
| `pair-finder/pairfinder/` | Pipeline code. Prompts are in `evaluate.py`; the judge's strong / weak / reject criteria are in `llm.py`. |
| `pair-finder/data/` | Cached papers, tags, and judged pairs. |
| `pair-finder/eval/run2/` | Main run: items, model runs, and grades. |
| `pair-finder/results/run2/` | Main run: all graded runs pooled (`scored_all.jsonl`), run notes, and the second-grader check, pass 2 (`regrade_gemma/`). |
| `analysis/main_run/` | Analysis of the main run as reported in the paper: scripts, tables, Figure 1, second-grader check pass 1, and a browser page for reading every graded run. |
| `controlled_experiment/` | Experiment 2: hand-built items, runner, every prompt and response, scoring script, Figure 2, results write-up, and a browser page for reading every brief. |

## Runs

| Run | What it was | Where |
|---|---|---|
| Pilot 1 (13 Nov) | 6 items, Claude subagents, one sample each. An illustration, not a result. | `pair-finder/results/pilot_run_2026-11-13.md` |
| Pilot 2 (14 Nov) | Hand-written items with one-line findings and a cite-every-source instruction; Claude Haiku, Sonnet, and Opus. All 12 conflict runs asserted the orphan conclusion. | `pair-finder/results/pilot2/` |
| Run 1 (14 Nov) | 39 macroeconomics items, 3 conditions, 4 open models, 2 samples: 935 runs, graded by glm-5.2. Showed that the pilot's rate did not hold at scale. Not reported in the paper. | `pair-finder/eval/` (top-level files), `pair-finder/results/full_run/` |
| Smoke test | 36-run check of the harness. | `pair-finder/eval/smoke/` |
| **Run 2: the paper's main run** (14 Nov) | Macroeconomics and cosmology, 3 input conditions with citing optional, probe ladder, 1 sample. 471 graded runs: 414 from the three main models, 45 from glm-5.2 (incomplete, gateway timeouts), 12 from a Claude Opus subset on a different harness. Graded by qwen3.8-27b. | `pair-finder/eval/run2/`, `pair-finder/results/run2/` |
| Second-grader check | gemma-4-31b-it relabeled a stratified sample of main-run paragraphs, twice. | Pass 1: `analysis/main_run/regrade.jsonl`. Pass 2: `pair-finder/results/run2/regrade_gemma/` |
| **Controlled experiment** (14-15 Nov) | 2 hand-built items, 8 conditions, 4 models, 5 samples: 320 briefs and 96 belief probes. | `controlled_experiment/` |

The paper excludes one main-run item, `conflict_W3023274331_W2021991108`. It was generated without an orphan statement, and the conclusion its Q2 tested is accepted by both frameworks. That leaves 32 conflict items and 282 conflict runs from the three main models. Files under `analysis/main_run/superseded_33_items/` predate the exclusion.

## Reproducing the paper's numbers

These steps need only Python 3 and matplotlib. No API keys.

```
cd analysis/main_run
python exclude_dropped_item.py            # writes scored_32.jsonl (459 runs)
python analyze.py scored_32.jsonl         # writes tables.json: Table 1, Table A1, Table A2
python make_figure.py scored_32.jsonl     # writes ladder_data.json and ladder.png
python grader_agreement.py                # second-grader agreement, both passes

cd ../../controlled_experiment
python score_and_report.py                # tables, Figure 2, browser page
```

`figure1_ladder.png` is the figure as it appears in the paper; `make_figure.py` redraws the same data as `ladder.png`.

Re-running the models needs API keys: see `pair-finder/REPRODUCE.md` for the main run and the header of `controlled_experiment/run_pretest.py` for the controlled experiment.

## Reading the raw outputs

Two offline pages show every model output next to its prompt and labels. Open them in a browser.

- `analysis/main_run/run2_browser.html`: every graded main-run paragraph, with sources, probe answers, and grader labels. It includes the excluded item.
- `controlled_experiment/pretest_browser.html`: all 320 briefs with follow-up answers and codes.

## Caveats

- Items, verdicts, and orphan statements were written by an LLM from abstracts and were not checked by subject experts.
- All main-run labels come from LLM graders, one of which was also a test model. The controlled-experiment briefs were coded by a single LLM reader, not blind.
- The controlled-experiment result rests on one hand-built item.
