# pair-finder

Finds candidate paper pairs for a benchmark on hidden theoretical conflict in conjunctions.

**Target pattern.** A model writes "X and Y", citing paper x for X and paper y for Y. X and Y look compatible. But x's claim depends on statement p of theory P, y's claim depends on statement q of theory Q, and p contradicts q. Same-conclusion agreement is out of scope.

**When it counts as an error.** Combining results from inconsistent models is often legitimate. A pair is only a target when an *orphan conclusion* exists: a claim that follows from X and Y together but that neither framework endorses (e.g. "debt-financed rebates raise spending at no cost to national saving"). If the conflict disappears once each claim is scoped to its own regime, the pair is `regime_scopable` and its scoped version is a legitimate control.

**Suggested scores.** (1) Does the model flag or scope the tension unprompted? (2) Asked directly, does it say p and q conflict? (3) Is it consistent between (1) and (2)? (4) Does it assert the orphan conclusion? Combining is not itself scored as wrong.

**Controls.** `control_same_P` / `control_same_Q`: both papers from one framework (conjunction is fine). `control_regime_scoped`: a conflict pair rewritten with each claim restricted to its regime. Hard negatives: `reject` rows that look like rivals but are not. `conjunction_anon` strips citations and framework names (`framework_terms` in the catalog) to test for memorised rivalries.

## How it works

1. **Catalog** (`frameworks.yaml`): 12 classical rival-framework splits (collapse vs Bohm, collapse vs Everett, IIT vs GNW, Keynesian vs New Classical, frequentist vs Bayesian, behaviorism vs cognitivism, nativism vs usage-based, ΛCDM vs MOND, EMH vs behavioral finance, inclusive fitness vs group selection, expected utility vs prospect theory, computationalism vs enactivism). Each framework has numbered core statements; `conflicts` lists the contradicting pairs (p, q). Edit freely; add `seed_dois` to force known papers in.
2. **fetch**: OpenAlex full-text search per side, top-cited with abstracts. Papers retrieved by both sides are dropped.
3. **tag** (1 LLM call per paper): main claim as it would be cited, which core statements it actually depends on, whether the claim reads framework-neutral, confidence.
4. **pair**: for each conflict (p, q), pairs x (side P, depends on p) with y (side Q, depends on q). Ranked by tag confidence, framework-neutral reading and topical similarity of the two claims; near-identical claims are dropped (same conclusion, not a conjunction). Top-k per split, each paper used at most twice.
5. **judge** (1 LLM call per kept pair): writes the conjunction a reviewer might produce, checks surface consistency and both dependences, states the two background statements and why they conflict, gives the orphan conclusion and whether the pair is regime-scopable, verdict strong / weak / reject. Same-framework controls (`--controls`, default 4 per split) get a conjunction only.
6. **export**: `data/pairs.csv` (with empty `human_verdict`, `human_notes` columns) and `data/pairs.jsonl` (full records incl. abstracts).

## Current data

`data/macro_pairs.csv`: Keynesian vs New Classical, 356 papers, tagged and judged by Claude in a Claude Code session (no API calls). 6 strong, 19 weak, 20 reject (hard negatives), 32 controls. Every listed conflict cites canonical statements of both positions (`p_sources`, `q_sources`) plus survey sources (Snowdon & Vane 2005; Greenwald & Stiglitz 1987; Ramey 2011). `eval/items.jsonl`: 39 eval items built from these pairs.

## Eval

`python -m pairfinder.evaluate build|run|score|report`. Buries the pair among distractors, asks an off-target policy question, probes the two premises directly in the same conversation, and grades. See REPRODUCE.md for commands, conditions and cost.

## Setup

```bash
pip install -r requirements.txt
export OPENALEX_API_KEY=...      # free: https://help.openalex.org/api/authentication/
export ADAPTION_API_KEY=...        # default backend (open models)
export ANTHROPIC_API_KEY=...       # optional, for claude-* models
```

## Run

```bash
python -m pairfinder list
python -m pairfinder run --splits consciousness_iit_vs_gnw,qm_collapse_vs_bohm   # fetch + tag + pair + judge
python -m pairfinder run                                                       # all 12 splits
python -m pairfinder pair --no-judge          # reuse cached tags, skip judge
python -m pairfinder pair --no-llm            # zero LLM cost: raw cross-side pairs by text similarity -> data/raw_pairs.csv
```

Stages cache to `data/papers/` and `data/tagged/`; `tag` resumes and skips papers already tagged. Re-running `fetch` or `run` refetches.

Flags: `--per-query` (OpenAlex results per query, default 10), `--min-citations` (10), `--top-k` (pairs per split, 6), `--min-conf` (0.6), `--model` (default `glm-5.2` on Adaption; `claude-*` ids use the Anthropic API), `--workers` (8).

**Cost.** All 12 splits at defaults is roughly 600 tagging calls and 72 judge calls: a few Adaption credits with `glm-5.2`, or $10–15 with `--model claude-opus-5-5`. Run one or two splits first. See REPRODUCE.md for eval costs.

## Test

```bash
python -m tests.test_offline   # fake OpenAlex + local stub of the Messages API; no keys needed
python -m tests.test_eval      # eval harness against the same stub
```

## Limits

- Retrieval is keyword search, so recall for each framework depends on the queries in `frameworks.yaml`.
- Dependence on a core statement is the LLM's judgment from the abstract only. Treat every row as a candidate; the human verdict is the label.
- The conflict list is hand-written. A pair whose backgrounds conflict on a statement not in the catalog will not be found.
