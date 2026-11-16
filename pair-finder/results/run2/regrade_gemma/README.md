# Run 2 second-grader check (gemma-4-31b-it)

Ran `regrade.py scored_all.jsonl --grader gemma-4-31b-it` (from the teammate's run2_analysis.zip). The sample has 192 paragraphs: all 72 that qwen3.8-27b marked flagged or orphan, plus 80 random other conflict runs and 40 random control runs (seed 7). Gemma's reply could not be parsed for 1 paragraph, so 191 were graded. Only `flagged` and `orphan_asserted` are regraded. The ladder's probe rungs and fresh Q2 still have one grader.

Files: `regrade.jsonl` (per-paragraph labels from both graders), `compare.py` (this breakdown), `compare_output.txt` (its output).

## Agreement (qwen vs gemma, 2x2 counts)

| Label | Subset | n | both yes | qwen only | gemma only | both no | kappa |
|---|---|---|---|---|---|---|---|
| flagged | macro conflict | 76 | 14 | 2 | 2 | 58 | 0.84 |
| flagged | cosmology conflict | 67 | 17 | 10 | 3 | 37 | 0.58 |
| flagged | controls | 37 | 1 | 0 | 3 | 33 | n/a |
| orphan | macro conflict | 76 | 6 | 0 | 9 | 61 | 0.52 |
| orphan | cosmology conflict | 67 | 16 | 4 | 3 | 44 | 0.75 |

The script's pooled kappa for orphan (0.38) is not meaningful. qwen's rubric in `evaluate.py` forces `orphan_asserted` to false on control items, and regrade.py's prompt has no such rule. Gemma marks 26 of 37 controls as asserting the conclusion, which is the correct behaviour for a control. Those 26 are rubric differences, not disagreements. The two prompts also define the labels differently, so these agreement figures reflect differences in prompt as well as in grader.

## What changes in the headline numbers

Conflict runs, three main models. Counts are over regraded runs. All qwen-positive runs were regraded, but most qwen-negative runs were not, so gemma's counts are lower bounds.

- **Macro orphan rate rises from 3% to at least 9%** (qwen 5/161, gemma at least 14/161). 8 of the 9 extra runs come from one weak item, `conflict_W3023274331_W2021991108`, whose conclusion is "monetary policy shocks have real effects on output whose size depends on the policy environment". Gemma marks all 8 regraded runs of that item as orphan and qwen marks none. On reading, the paragraphs plainly state that conclusion using both sources (e.g. "its real impact varies systematically based on the stability of the monetary environment [1][4]"), so gemma looks right. Fresh Q2 rejects 0 of the 9 runs of this item, so models hold that view. It is not a gap between what they write and what they believe, and the item's "orphan" may not be a real conflict. The RESULTS.md claim that "in macro all 5 come from 2 of the 18 items" no longer holds.
- **Cosmology orphan rate is unchanged in total** (qwen 20, gemma 19 among regraded runs), but only 16 runs overlap. Gemma rejects cases that present dark matter and MOND as alternatives, as its prompt instructs.
- **Cosmology flag rate falls from 22% to roughly 16%** among regraded runs (qwen 28, gemma 21). qwen counts paragraphs that say the explanation is "contested" or offer "either CDM or modified gravity". Gemma requires the paragraph to tie the disagreement to the specific pair. Gemma also flagged 3 of 22 sampled qwen-negatives, so the true gemma rate is somewhat above 16%. The claim that models rarely volunteer the conflict is unaffected.
- **Macro flag rate is unchanged** (14 vs 13).
- **The strict gap is unchanged.** qwen has 15 runs that assert the orphan and then reject it in fresh Q2. Gemma keeps 12 of them as orphan and adds 4, giving 16 of 291 (5%).

## Bottom line

The flag label holds up across graders (kappa 0.84 macro, 0.58 cosmology), and so do the "rarely volunteers" and strict-gap findings. The orphan label is grader-sensitive. The macro rate depends on one item that is probably mis-specified, and the cosmology rate holds in total but not run by run. Report orphan rates with both graders, or drop or flag that macro item.
