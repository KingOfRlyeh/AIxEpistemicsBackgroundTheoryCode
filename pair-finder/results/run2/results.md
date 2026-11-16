# Run 2 results (2026-11-14)

## What changed from run 1

- **Two fields.** Macro (Keynesian vs new classical): 26 items, made up of 18 conflict, 4 same-theory controls, and 4 regime-scoped controls. Cosmology (ΛCDM dark matter vs MOND): 21 items, made up of 15 conflict and 6 same-theory controls.
- **Three conditions.** In all three, citing every source is optional.
  - `findings`: 6 one-line findings. This is the "lossy summary fed to another model" case.
  - `abstracts`: 12 full abstracts.
  - `abstracts_anon`: 12 abstracts with the theory names replaced by `[theory name removed]`.
- **A probe ladder after each paragraph, in one conversation:**
  1. A generic self-review ("any problems with how it combines the sources?").
  2. "Do any sources conflict?"
  3. The direct Q1 and Q2 about the specific pair.
  4. The same Q1 and Q2 in a fresh conversation that has the sources but no paragraph.
- **Reworded soft items.** The 3 soft demand-vs-technology items now state the strong claims.
- **Models:** deepseek-v4-flash, qwen3.5-397b and qwen3.8-27b, with 1 sample each.
  - glm-5.2 was dropped partway through. Adaption's endpoint for it returned 504s for hours. It completed only 45 of 141 runs; those runs are in `report.md` but not in the pooled tables.
  - A Claude subset ran as Claude Code subagents: 6 macro items × 2 conditions.
- **Grader:** qwen3.8-27b. glm-5.2 graded run 1 but was down for this run. qwen3.8-27b is also a test model, so it grades its own runs.
- **Volume and cost:** 459 graded Adaption runs. The runs cost about 12.9 credits, and grading was a few more.

## Results (conflict items, 3 models pooled)

| field | condition | n | cited both | flagged in paragraph | unflagged orphan | self-review flags pair | "do sources conflict?" flags pair | Q1 says incompatible | fresh Q1 incompatible |
|---|---|---|---|---|---|---|---|---|---|
| macro | findings | 53 | 87% | 19% | 6% | 19% | 53% | 89% | 92% |
| macro | abstracts | 54 | 56% | 6% | 2% | 4% | 33% | 98% | 94% |
| macro | abstracts_anon | 54 | 52% | 2% | 2% | 6% | 37% | 96% | 96% |
| cosmo | findings | 43 | 100% | 19% | 21% | 23% | 51% | 91% | 98% |
| cosmo | abstracts | 43 | 95% | 23% | 12% | 16% | 63% | 93% | 98% |
| cosmo | abstracts_anon | 44 | 89% | 23% | 9% | 16% | 52% | 89% | 95% |

"Unflagged orphan" means the paragraph asserted the orphan conclusion without flagging the conflict. This is the scored error.

## Findings

1. **Models know about the conflict, but they don't tell the reader.**
   - Asked directly, they call the pair incompatible 89-98% of the time, with or without the paragraph in context.
   - In the paragraph a person actually reads, they flag it 2-23% of the time.
   - When both sources are cited, most paragraphs simply set them side by side with no flag: 27 of 30, 27 of 28 and 36 of 46 in macro; 31 of 41, 29 of 39 and 35 of 43 in cosmology.
2. **A generic self-review does not surface the conflict.** "Any problems with how it combines the sources?" catches the pair 4-23% of the time. "Do any sources conflict?" catches it 33-63%. Only the question about the specific pair gets near 90%+. A reader who does not already know the conflict exists has no way to ask that question.
3. **One-line findings are the worst input for orphan conclusions in cosmology: 21%, against 9-12% with abstracts.**
   - This is the case where one model's summary feeds another.
   - Every cosmology findings run cited both sources.
   - Some of these orphans are hedged reconciliations, such as "the scatter is also consistent with ΛCDM… even if a universal acceleration scale dominates", rather than outright false claims.
   - In macro, orphans are rare in every condition (1-3 per 54). Run 1 had 13% with findings and cite-all.
4. **Removing theory names barely matters.** Flag rates, orphan rates and Q1 all move by a few points. The models are not relying on the labels to recognize the conflict.
5. **The reworded items are still the hard spot.** On the 8 conflict items involving the 3 reworded papers, Q1 is 88% (63 of 72). On all other macro conflict items it is 100% (89 of 89).
6. **Controls:**
   - The paragraph flagged a same-theory control 1 time in 123 runs.
   - Same-theory controls are almost never called incompatible: 1 of 90 on Q1.
   - Regime-scoped controls get "incompatible" on Q1 in 27 of 33 runs. Those theories really do make different assumptions, and Q1 asks about assumptions, so this is a correct answer, not a false alarm. On these items, the paragraph flag and Q2 are the measures to read.
7. **Claude subset.** These are 6 macro conflict items per condition, graded by qwen3.8-27b.

   | | findings | abstracts_anon |
   |---|---|---|
   | flagged in paragraph | 2 of 6 | 1 of 6 |
   | unflagged orphan | 0 | 0 |
   | self-review flags pair | 2 of 6 | 0 of 6 |
   | "do sources conflict?" flags pair | 6 of 6 | 5 of 6 |
   | Q1 incompatible | 6 of 6 | 6 of 6 |

   This is the same pattern as the other models, at a smaller size. glm-5.2 had graded 2 of the findings paragraphs as orphans; qwen3.8-27b grades 0.

## Why this matters

- **People read the paragraph, not the probe answers.** The model has the knowledge (Q1 is about 90% or higher), but a reader sees a smooth synthesis with a flag in at most about a fifth of cases. A reader who doesn't already know the field has no way to know which follow-up to ask, and the generic "check your work" review mostly comes back clean.
- **Lossy summaries feed other models.** The one-line findings condition models an AI-written summary used as input. It gives the highest rate of citing both sources, and in cosmology the highest orphan rate. The next model inherits the side-by-side placement with no flag.

## Caveats

- The grader is qwen3.8-27b, which is also a test model. Run 1 used glm-5.2, so numbers do not compare exactly across runs.
- Cosmology findings often name the theory ("MOND fits…"), so the findings condition shows the conflict more openly there than in macro.
- Several macro findings name theories or authors ("New Keynesian", "Ricardian").
- glm-5.2 is incomplete.
- The Claude subset ran as Claude Code subagents (agent system prompt and file reads), not through the raw API.
- I wrote the rewordings of the 3 soft items myself, from the abstracts.

## Files

- `eval/run2/`: items, runs and scored output for both fields, plus `claude/` for the subset.
- `results/run2/report.md`: the table broken out by model.
- `results/run2/scored_all.jsonl`: all graded runs.
- `results/run2/pooled.py`: produces the pooled table.
