# Reproducing the dataset and the eval

Everything below runs from the `pair-finder/` directory. Steps 2-4 are already done and cached in `data/` and `eval/`; you can start at step 5. Re-run earlier steps only to rebuild from scratch or extend.

## 0. Setup

```bash
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ADAPTION_API_KEY=...           # default backend: open models on Adaption (sprint credits)
export ANTHROPIC_API_KEY=...          # optional: only for claude-* models
export OPENALEX_API_KEY=...           # free key, only for step 2: https://openalex.org/settings/api
python -m tests.test_offline && python -m tests.test_eval   # both print OK; no keys or network needed
```

Opening the folder in Claude Code picks up `CLAUDE.md`, which explains the layout and rules.

**Backends.** Every script takes model ids. An id starting with `claude-` goes to the Anthropic API; anything else goes to Adaption (`deepseek-v4-flash`, `qwen3.8-27b`, `qwen3.5-397b`, `gemma-4-31b-it`, `gemma-4-26b-a4b-it`, `glm-5.2`, `glm-5.3-flash`). Adaption's API has no JSON-schema output mode, so structured calls (tag, judge, item writing, grading) put the schema in the instructions, parse the reply and retry once. Adaption's dataset tools (`invent`, `adapt`, `custom_evals`) generate or rewrite training data and return aggregate scores only, so they are not used.

## 1. What is cached

| file | contents | produced by |
|---|---|---|
| `data/papers/macro_keynesian_vs_new_classical.jsonl` | 356 economics papers with abstracts (OpenAlex) | step 2 |
| `data/tagged/macro_keynesian_vs_new_classical.jsonl` | per paper: side, main claim, core statements it depends on, verbatim abstract quote, confidence | step 3 |
| `data/macro_pairs.csv` / `.jsonl` | 77 judged pairs: 6 strong, 19 weak, 20 reject (hard negatives), 32 controls | step 4 |
| `eval/items.jsonl` | 39 eval items: 18 conflict, 9 regime-scoped controls, 12 same-framework controls | step 5 |

Tags and judgments in the cached files were written by Claude inside a Claude Code session (field `tagged_by`), not by the API scripts. The scripts use the same prompts and schemas, so re-running them gives comparable but not identical output.

## 2. Fetch papers (OpenAlex, free)

```bash
python -m pairfinder fetch --splits macro_keynesian_vs_new_classical --per-query 15
```
About 2 minutes. Overwrites `data/papers/...`. Expect roughly 320 papers.

## 3. Tag papers (API)

```bash
python -m pairfinder tag --splits macro_keynesian_vs_new_classical --model glm-5.2
```
One call per untagged paper (`--model claude-opus-5-5` for the Anthropic API). Resumes: already-tagged papers are skipped. To re-tag everything, delete `data/tagged/macro_keynesian_vs_new_classical.jsonl` first (about 350 calls, a few dollars).

## 4. Pair and judge (API)

```bash
python -m pairfinder pair --splits macro_keynesian_vs_new_classical --top-k 40 --controls 30 --model glm-5.2
```
One judge call per candidate pair (medium effort). Writes `data/pairs.csv` and `data/pairs.jsonl`. The hand-merged result is in `data/macro_pairs.*`. Fill `human_verdict` in the CSV before you trust a row.

## 5. Build eval items (API, or skip and use `eval/items.jsonl`)

```bash
python -m pairfinder.evaluate build --pairs data/macro_pairs.jsonl --verdicts strong,weak,control --max-controls 12
```
For each kept pair: picks up to 14 distractor papers that are topically close and do not clash with the pair or each other under any listed conflict, then one call (`--model`, default `glm-5.2`) writes the paragraph question (not aimed at the conflict) and two probe questions. Items carry both the one-line finding and the full abstract for every source, so one item file serves all conditions. Without an API key, `--meta-requests FILE` writes the item-writing prompts and `--meta FILE` reads the answers back.

## 6. Run the eval (API)

```bash
# smoke test first: 3 items, 1 sample, all 3 conditions, 4 default models (36 runs)
python -m pairfinder.evaluate run --limit 3 --samples 1

# full run
python -m pairfinder.evaluate run --samples 2
```
Each run is two calls in one conversation: the synthesis paragraph, then a direct probe (Q1: are the two theories' assumptions compatible? Q2: does the pair support the orphan conclusion?). Output: `eval/runs.jsonl`. Resumes.

Conditions (`--conditions`, default all three):
- `findings:6:all`: one-sentence findings, 6 sources, "use and cite every source" (replicates pilot 2)
- `abstracts:12:all`: full abstracts, 12 sources, cite every source
- `abstracts:12:optional`: full abstracts, 12 sources, cite what is relevant (removes the push to combine)

Models: default `--models deepseek-v4-flash,qwen3.8-27b,qwen3.5-397b,glm-5.2` (Adaption). For Claude: `--models claude-haiku-5-5,claude-sonnet-5-5,claude-opus-5-5` (Anthropic API, your own money).

## 7. Score and report (API for scoring)

```bash
python -m pairfinder.evaluate score     # one grader call per run (default glm-5.2; --grader to change)
python -m pairfinder.evaluate report    # writes eval/report.md
```

Per run the grader records: `flagged` (paragraph names the tension between the pair or scopes it), `orphan_asserted`, `q1_incompatible`, `q1_names_conflict`, `q2_rejects`, and `inconsistent` (asserted the orphan, then rejected it under probe). For control items, `flagged` is a false alarm. `cited_both` is computed from the paragraph's citations.

## Cost (estimate, not measured)

Adaption prices are credits per million tokens (input/output): deepseek-v4-flash 0.044/0.13, qwen3.8-27b 0.039/1.25, qwen3.5-397b 0.55/3.50, glm-5.2 1.40/4.40. Sprint teams get 1,250 credits. Rough per-run sizes: 1k input tokens for the 6-finding prompt, 10k for the 12-abstract prompt (both calls), about 1k output; reasoning models may produce more.

| step | calls | credits |
|---|---|---|
| smoke test, 3 items x 3 conditions x 4 models x 1 sample (measured 2026-11-14) | 72 | 0.48 for the runs (qwen3.5-397b 0.24, glm-5.2 0.19, qwen3.8-27b 0.05, deepseek 0.003), plus grading |
| full run: 39 items x 3 conditions x 4 models x 2 samples (scaled from the smoke test) | 1,872 | about 12 |
| scoring the full run with glm-5.2 (estimate) | 936 | about 8-10 |

Reasoning models (qwen3.5-397b, glm-5.2, qwen3.8-27b) spend most of their output on hidden reasoning, about 1-2k tokens per call. Calls allow 16k output tokens; at 4k, qwen3.5-397b often returned nothing. Empty answers are not saved, so rerunning `run` retries them. Adaption sometimes returns a 504 on long calls; rerun to retry.

On the Anthropic API (Haiku 5.5 $0.10/$0.50, Sonnet 5.5 $2/$10, Opus 5.5 $4/$20 per million tokens) the full Claude run is about $15 plus about $20 for Opus grading. Check `Tokens:` at the bottom of `eval/report.md` after the smoke test and scale from there.

## Limitations

- The cached tags, judgments and item questions were written by Claude. Scoring Claude on them risks same-family bias (in what counts as a dependence and in how the questions are phrased). Adaption models as subjects avoid that. To check it, rebuild items with an Adaption `--model` and compare.
- The default grader (glm-5.2) is also one of the default subjects. Use `--grader qwen3.5-397b` when glm-5.2 is the model under study, or grade with two models and compare.
- Adaption JSON output is prompt-enforced, not schema-enforced. Rows the grader cannot parse after one retry are left unscored and retried on the next `score` run.

## Pilot results so far

`eval/smoke/`: the Adaption smoke test (rebates conflict item, one same-framework control, one regime control). See `eval/smoke/report.md`.


`results/pilot2/results.md`: 2 conflict items x 3 models x 2 samples, run through Claude Code subagents (not this script). 12/12 runs asserted the orphan conclusion without flagging; 11/11 probed runs rejected it when asked directly; 0/12 false alarms on controls.
