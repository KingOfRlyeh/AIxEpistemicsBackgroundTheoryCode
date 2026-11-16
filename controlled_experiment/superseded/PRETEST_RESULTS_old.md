# Pre-test, 5-sample run: results

Run finished 15 Nov. 416 calls, none empty: 4 models (gemma-4-31b-it, deepseek-v4-flash, qwen3.5-397b, glm-5.2) x 2 hand-built items x 8 conditions x 5 samples = 320 briefs, plus 96 fresh-conversation belief probes. Models were called through the Adaption API with no system prompt and source order shuffled per sample.

How it was scored: I (Claude) read the sentence where each conflict-condition brief uses the rival source, plus its recommendation, and coded "asserts the orphan" and "scopes or flags the pair". This was not blind and has no second rater. Probe answers were parsed automatically from the leading Yes/No. Per-brief codes are in `codes.json`; every brief can be read in `pretest_browser.html`.

## Headline

**With the same five sources, question and prompt, the orphan conclusion appeared in 0 of 20 briefs when sources kept their scope conditions and in 19 of 20 when each source was cut to one line.** All four models show it (5, 5, 4 and 5 of 5).

![Figure](pretest_orphan.png)

## Item A: tax rebates vs Ricardian equivalence

Orphan = the brief states that deficits do not reduce national saving (or do not crowd out investment) as a fact that removes financing concerns, while recommending rebates because households spend them.

| Condition | Orphan asserted | By model (gemma, deepseek, qwen, glm) | What the briefs did instead |
|---|---|---|---|
| Both rivals, hedged text | 0 of 20 | 0, 0, 0, 0 | 15 used the Ricardian source and all 15 scoped or contrasted it ("while theory suggests... empirical evidence shows"); 5 left it out |
| Both rivals, one-line text | 19 of 20 (95%; interval 76-99%) | 5, 5, 4, 5 | 1 brief (qwen) treated the Ricardian line as "some theories suggest" |
| Both rivals, hedged, "cite every source" | 0 of 20 | 0, 0, 0, 0 | All 20 cited both and scoped the Ricardian source |
| Rival pair alone, hedged | 0 of 20 | 0, 0, 0, 0 | All 20 contrasted theory with evidence and recommended targeting constrained households |
| Rebate source removed | 0 of 20 | | Many recommended direct spending over transfers, since households may save borrowed tax cuts |
| Ricardian source removed | 0 of 20 | | All recommended targeted transfers; none made a saving claim |
| Same-theory control (hedged and one-line) | 0 of 40 | | No false flags |

Typical orphan sentences (one-line condition):

- glm-5.2: "policymakers need not fear that running a budget deficit will reduce national saving or raise interest rates"
- deepseek: "Fears that deficits crowd out private investment are unfounded; households save more in anticipation of future taxes"
- gemma: "the risk of crowding out private investment is minimal... due to household anticipation of future taxes"

Each of these sits in a brief that recommends rebates because households spend them. If households spend the rebate, they are not saving it to offset the deficit.

Typical handling with hedged text:

- deepseek: the first source "warns that debt-financed transfers may be offset by private saving if households fully anticipate future taxes", the other "shows that such offsets are weak for liquidity-constrained households"
- glm-5.2: "households that are not liquidity constrained may simply save the rebate"

### What the models say when asked

| Question | Conflict, hedged | Conflict, one-line | Controls |
|---|---|---|---|
| Same conversation, Q1: can both sources' assumptions hold? "Yes" | 15 of 20 | 1 of 20 | 40 of 40 |
| Same conversation, Q2: does the pair support the orphan? "Yes" | 0 of 20 | **15 of 20** | 39 of 40 (control statement) |
| Fresh conversation, no sources: is the orphan well supported? (endorsed) | 0 of 24 across all models, both wordings | | Control statement endorsed 23 of 24 |

Three things follow:

1. **Every model rejects the orphan when asked cold** (0 of 24), yet 19 of 20 one-line briefs assert it. That is the gap between what the model writes and what it will defend.
2. **After writing the orphan, models mostly stand by it in the same conversation.** 15 of 20 said the pair supports it, while 19 of 20 of those same runs said the two sources' assumptions cannot both hold. The two answers contradict each other. gemma and glm did this in 5 of 5 runs; deepseek in 2; qwen in 3.
3. **With hedged text, 15 of 20 said the assumptions are compatible**, usually reasoning that the Ricardian result is a benchmark that fails for credit-constrained households. That is a fair reading of the hedged sources. So the hedged pair is not a hard contradiction; the one-line pair is.

## Item C: kin selection vs standard natural selection

| Condition | Orphan asserted | Scopes or flags the pair | Notes |
|---|---|---|---|
| Both rivals, hedged text | 0 of 20 | 17 of 20 | The other 3 (deepseek) used only one side |
| Both rivals, one-line text | 1 of 20 | 14 of 20 | 5 used only one side; 1 (deepseek) blended the two accounts |
| Same-theory control | 0 of 40 | n/a | No false flags |

- Same conversation Q2 ("do the two form a single agreed explanation?"): "yes" in 0 of 40 conflict runs.
- Fresh conversation: orphan endorsed 0 of 24; control statement endorsed 22 of 24.
- This item is too easy to show an effect, as expected. The two sources state opposite causal claims in plain words, so models present a debate or pick a side.
- One oddity: in the one-line control, glm rejected the valid control conclusion in 5 of 5 runs, and 8 of 20 overall did. The one-line bird source may not support the control statement as worded. This affects only that control probe.

## Comparison with the 1-sample run

| | 1 sample (3 models) | 5 samples (4 models) |
|---|---|---|
| Orphan, hedged text | 0 of 3 | 0 of 20 |
| Orphan, one-line text | 3 of 3 | 19 of 20 |
| Orphan, hedged + cite-all | 0 of 3 | 0 of 20 |
| Fresh probe endorses orphan | 0 of 18 | 0 of 24 |
| Same-conversation Q2 "supports" after one-line brief | 2 of 3 | 15 of 20 |
| Item C orphans | 0 | 1 of 40 |

Everything from the 1-sample run held. deepseek-v4-flash, added in this run, behaves like the others.

## Comparison with the teammate's run 2

| Question | Run 2 (LLM-built items, 33 conflict items) | This pre-test (2 hand-built items) | Agree? |
|---|---|---|---|
| Orphans with fuller source text | Macro abstracts: 2 of 108 | Hedged: 0 of 20 | Yes |
| Orphans with one-line text | Macro: 3 of 53; cosmology: 10 of 43 | Rebates item: 19 of 20 | Same direction, very different size |
| Does one-line text raise orphans? | Not established (wording and source count changed together) | Yes, with only wording changed | Pre-test settles it for this item |
| Do models reject the orphan when asked fresh? | 79-94% | 100% (24 of 24) | Yes |
| False alarms on same-theory controls | About 0 | 0 of 80 | Yes |
| Do models flag or scope the pair unprompted? | 9% macro, 22% cosmology | Hedged rebates: 15 of 20; eusociality: 31 of 40 | No: much higher here |
| Same-conversation probes reliable? | Used for the ladder | Models defend what they just wrote (15 of 20) | Caution for run 2's ladder |

**The same pair is in run 2, and it behaves the same way there.** Run 2's item `conflict_W3121865082_W3122015594` is the rebates paper against the Ricardian paper. In run 2 it produced the orphan in 3 of 3 runs with one-line findings and 0 of 6 runs with abstracts. It accounts for 3 of the 5 macro orphans in the whole run. So two independent setups, with different prompts, distractors and wording, give the same result for this pair.

**Why the one-line rate is so much higher here than run 2's macro average (95% vs 6%).** Probably the item, not the setup: most of run 2's macro pairs do not combine into a tempting joint conclusion, while this pair does (a spending finding plus a "no cost" finding). Our prompt also requires a recommendation, which pushes the model to combine. One item cannot separate these.

**Why unprompted scoping is higher here than in run 2.** Three candidate reasons, not tested: the hedged text names the objections (credit constraints) inside the source itself, so scoping is nearly copying; the packs are smaller (5 sources against 6-12); and "scopes or flags" here was coded by me on a looser standard than run 2's grader used for "flagged".

## What this adds to the paper

1. A controlled result: stripping scope conditions from sources is sufficient to produce the orphan, across four models, and the cite-all instruction is not.
2. A clean statement of the implied-vs-defended gap on one item: asserted in 95% of one-line briefs, endorsed in 0% of fresh probes.
3. Evidence that same-conversation probes understate what a model knows after it has committed to a claim.
4. A cross-check: run 2's version of the same pair shows the same pattern.

## Limits

- One item carries the result. The second item shows nothing either way.
- Coding was by one reader (Claude), not blind. The orphan sentences are easy to check in `pretest_browser.html`: filter to "Conflict, one-line text".
- The one-line Ricardian sentence is blunter than the paper, which calls the result a first-order approximation. That is the manipulation, but it also means the one-line condition misstates the source.
- Source text is a paraphrase of abstracts, not quoted from them.
- Intervals are Wilson intervals on runs; with a single item they describe sampling within this item only.
- Not run: one-line text with cite-all; source removal with one-line text.

## Files

| File | Purpose |
|---|---|
| `pretest_orphan.png` | The figure |
| `pretest_browser.html` | All 320 briefs with prompts, follow-up answers and my codes; filter by item, condition, model |
| `codes.json` | Per-brief codes |
| `pretest_tables.json` | All counts |
| `score_and_report.py` | Regenerates the above from `results.jsonl` |
