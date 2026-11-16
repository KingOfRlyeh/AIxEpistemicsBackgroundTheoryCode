# Run 2 results, reanalysed by item

Source: `scored_all.jsonl` (471 graded runs). Main tables use the three complete models (deepseek-v4-flash, qwen3.5-397b, qwen3.8-27b): 291 conflict runs over 33 items, 123 control runs over 14 items. glm-5.2 (45 runs, incomplete) and the Claude Opus subset (12 runs, via subagents) are reported separately. All labels come from one LLM grader (qwen3.8-27b). Intervals are 95% bootstrap intervals that resample items, so they are wider than the run counts suggest.

## The short version

1. **Asserting the orphan is uncommon.** 5 of 161 conflict runs in macro (3%), 20 of 130 in cosmology (15%). In macro all 5 come from 2 of the 18 items.
2. **Models almost never volunteer that the pair comes from rival theories.** The paragraph flags the pair in 9% of macro conflict runs and 22% of cosmology runs.
3. **They recognise it readily when asked about the pair.** 96% (macro) and 92% (cosmology), against 3% and 6% for same-theory controls.
4. **A generic self-review barely helps.** "Any problems with how it combines the sources?" lifts detection from 9% to 14% (macro) and 22% to 33% (cosmology).
5. **Models separate illegitimate from legitimate combinations when asked.** In a fresh conversation they reject the orphan conclusion for 87-94% of macro conflict runs, 0% of same-theory controls and 0-9% of regime-scoped controls.
6. **The strict "says one thing, believes another" case is rare:** 15 of 291 conflict runs (5%) assert the orphan and then reject it in a fresh conversation.

## Figure

![Ladder](ladder.png)

Cumulative share of runs in which the model has flagged the pair by each step (three models and three input conditions pooled):

| | In the paragraph | + generic self-review | + "do any sources conflict?" | + asked about the pair (Q1) |
|---|---|---|---|---|
| Macro, conflict (18 items, 161 runs) | 9% [3-16] | 14% [8-21] | 46% [31-62] | 96% [91-99] |
| Macro, regime-scoped control (4 items, 33 runs) | 3% [0-9] | 6% [0-17] | 33% [12-57] | 82% [48-100] |
| Macro, same-theory control (4 items, 36 runs) | 0% | 0% | 3% [0-8] | 3% [0-8] |
| Cosmology, conflict (15 items, 130 runs) | 22% [8-37] | 33% [18-50] | 60% [44-76] | 92% [84-99] |
| Cosmology, same-theory control (6 items, 54 runs) | 0% | 0% | 6% [0-17] | 6% [0-17] |

**How to read it.** The ladder measures whether the model recognises that two sources come from different theoretical frameworks. That is why regime-scoped controls (rival theories, legitimately combinable) climb almost as high as conflict pairs, and same-theory controls stay flat. It does not measure whether the model thinks the combination is wrong; the fresh Q2 column below does that.

![Disclosure gap](disclosure_gap.png)

Figure 2 shows the same gap from the other side: how often the paragraph flags the pair unprompted, against how often the model rejects the joint conclusion when asked in a fresh conversation.

## Results by field and input

Conflict items only. "Knows" = rejects the orphan conclusion in a fresh conversation (fresh Q2).

| Field | Input | Runs | Cited both | Flagged in paragraph | Flagged, given cited both | Orphan asserted | Knows (fresh Q2) | Strict gap | Disclosure gap (knows minus flagged) |
|---|---|---|---|---|---|---|---|---|---|
| Macro | one-line findings | 53 | 87% | 19% [6-37] | 22% | 6% [0-17] | 87% [74-96] | 4% [0-12] | 68 pts [47-87] |
| Macro | abstracts | 54 | 56% | 6% [0-11] | 10% | 2% [0-6] | 94% [83-100] | 2% [0-6] | 89 pts [76-98] |
| Macro | abstracts, names removed | 54 | 52% | 2% [0-6] | 4% | 2% [0-6] | 93% [81-100] | 2% [0-6] | 91 pts [78-100] |
| Cosmology | one-line findings | 43 | 100% | 19% [2-40] | 19% | 23% [7-40] | 79% [58-95] | 12% [0-25] | 60 pts [25-87] |
| Cosmology | abstracts | 43 | 95% | 23% [7-43] | 24% | 14% [4-25] | 81% [60-98] | 9% [0-20] | 58 pts [21-86] |
| Cosmology | abstracts, names removed | 44 | 89% | 23% [9-38] | 26% | 9% [0-21] | 84% [64-100] | 5% [0-11] | 61 pts [39-82] |

Controls, for comparison (all inputs pooled): same-theory pairs are flagged in 0 of 90 paragraphs and the fresh Q2 rejects 0 of 90. Regime-scoped pairs are flagged in 1 of 33 and fresh Q2 rejects 2 of 33.

Notes on this table:

- With abstracts in macro, only about half the paragraphs cite both sources at all. The "given cited both" column is the fairer flag rate, and it is still low (4-22%).
- Differences between inputs are within the intervals. The data do not establish that one-line findings are worse than abstracts, and that condition also has 6 sources where the others have 12.
- Removing theory names makes no visible difference.

## By model

Conflict items, all inputs pooled.

| Model | Field | Runs | Flagged | Orphan | Knows | Strict gap | Mean rung (0-4, lower = volunteers sooner) |
|---|---|---|---|---|---|---|---|
| deepseek-v4-flash | macro | 54 | 13% | 2% | 89% | 2% | 2.46 |
| qwen3.5-397b | macro | 54 | 6% | 6% | 93% | 4% | 2.30 |
| qwen3.8-27b | macro | 53 | 8% | 2% | 92% | 2% | 2.30 |
| glm-5.2 (incomplete) | macro | 35 | 6% | 3% | 80% | 3% | 2.43 |
| claude-opus-5-5 (subagent) | macro | 12 | 25% | 0% | 100% | 0% | 1.50 |
| deepseek-v4-flash | cosmology | 44 | 25% | 23% | 82% | 11% | 1.89 |
| qwen3.5-397b | cosmology | 42 | 24% | 10% | 86% | 10% | 1.81 |
| qwen3.8-27b | cosmology | 44 | 16% | 14% | 77% | 5% | 2.09 |

"Mean rung" is the elicitation-depth score: 0 = flagged in the paragraph, 1 = at the generic review, 2 = at "do any sources conflict?", 3 = when asked about the pair, 4 = never. The three complete models are close to each other. The Claude subset is 12 runs under a different harness and should not be compared directly.

## Things the reanalysis turned up

1. **Orphans cluster in a few items.** Macro: 2 of 18 items produce all 5. Cosmology: 8 of 15 items produce the 20, and one item produces 4 of its 6 runs. Per-item reporting matters.
2. **When a model asserts the orphan, it is less likely to reject it later.** Fresh Q2 rejects the orphan in 15 of 25 orphan runs (60%) against 238 of 266 other conflict runs (89%). So about 40% of graded orphans are the model's stated view, not a gap between writing and belief.
3. **Macro strong vs weak items.** Strong: orphan 3 of 44, Q1 44 of 44. Weak: orphan 2 of 117, Q1 108 of 117. The weak items are slightly less recognisable as conflicts, as expected.
4. **The orphan labels look noisy on reading.** I read the first-graded orphan run for 7 different items in the one-line condition (not blind, no subject expertise):
   - About 2 are clear cases, e.g. a paragraph crediting sources [3][4] jointly for a relation "including the dark matter contribution" where one source frames it as MOND.
   - 1 reports a single source's claim without relying on the other ("findings that budget deficits do not raise real interest rates... [5]").
   - About 4 present the two views as alternatives or stay neutral, e.g. "regardless of whether the missing mass is dark or due to modified gravity" and "MOND offers a compelling alternative". That is arguably good practice, not an error.
   - Some orphan definitions are themselves defensible statements, e.g. "the baryonic Tully-Fisher relation is an empirical pattern that does not distinguish between" the two explanations.
   
   Treat the cosmology orphan rate in particular as an upper bound until a second grader or a person checks it.

## Second-grader check (added 14 Nov, evening)

A second model (gemma-4-31b-it) regraded 189 paragraphs with a separately written rubric: every paragraph the first grader marked flagged or orphan, plus a random 80 other conflict runs and 40 control runs. Agreement on the 148 conflict runs:

| Label | Agreement | Cohen's kappa | Both yes | First grader only | Second grader only | Both no |
|---|---|---|---|---|---|---|
| Flagged in paragraph | 86% | 0.65 | 30 | 16 | 5 | 97 |
| Orphan asserted | 90% | 0.68 | 22 | 4 | 11 | 111 |

What this shows:

- **The two graders agree substantially on both labels.** The orphan label held up better than my reading of 7 examples suggested.
- **The first grader is the more generous one on flags.** 16 of its 46 flags were not confirmed, 13 of them in the two abstract conditions. So the low unprompted flag rates in the tables are, if anything, too high. The "rarely volunteers" finding is conservative.
- **The second grader finds somewhat more orphans** (33 against 26 in this sample). 7 of its 11 extra orphans come from a single item (`conflict_W3023274331_W2021991108`) that the first grader never marked. That item should be read by a person, or reported separately.
- **Control runs are excluded from this table.** For controls the "conclusion under test" is a valid one, so a paragraph asserting it is not an error; the second grader marked 29 of 41 control paragraphs as asserting it, which is expected and not a disagreement about quality. On same-theory controls the second grader flagged 3 of 29 paragraphs where the first flagged none.

Caveats: the sample over-represents paragraphs the first grader marked positive, so these are not population agreement rates; the second grader used my rubric wording, not the first grader's prompt; both graders are LLMs and neither was checked against a person.

Sentence for the paper: "A second grader model (gemma-4-31b-it) relabelled a stratified sample of 148 conflict-item paragraphs; agreement with the primary grader was 86% for unprompted flags (kappa 0.65) and 90% for orphan assertions (kappa 0.68)."

## What the paper can claim from this

- **Supported:** models recognise rival-framework pairs when asked specifically (ladder top vs controls); they rarely volunteer it (ladder bottom); a generic review prompt adds little; in a fresh conversation they reject the joint conclusion for conflict pairs and accept it for controls.
- **Supported with the hand-built pre-test:** orphan assertions are rare when scope conditions are present and appear when sources are reduced to flat one-liners (see `01_pretest_results.md`; one item, small n).
- **Not supported:** that one-line findings are worse than abstracts in this run; that models differ from each other; any claim about how often a missing flag harms a reader, since nothing records whether the paragraph's conclusion depends on both sources.
- **Must be stated:** one LLM grader, also a test model; items written and judged by Claude with no expert check; one sample per item per model.

## Files

| File | Purpose |
|---|---|
| `analyze.py` | Recomputes every number here from `scored_all.jsonl`; writes `tables.json` |
| `make_figure.py` | Draws `ladder.png`; writes `ladder_data.json` |
| `regrade.py` | Second-grader check on a 192-paragraph sample; prints agreement and Cohen's kappa. Not yet run (needs the Adaption key) |
| `make_figure2.py` | Draws `disclosure_gap.png` (Figure 2) |
| `make_tables_html.py` | Writes `tables_for_doc.html`: Tables 1-4 as real tables for pasting into Google Docs |
| `tables.json`, `ladder_data.json` | All numbers, machine-readable |
| `run2_browser.html` | Every graded run on one page: sources (rival pair highlighted), paragraph, probe answers and grader labels, with filters for field, input, type, model and "orphan asserted". Open it in a browser; it works offline |
