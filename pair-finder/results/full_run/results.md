# Full run (Adaption, 2026-11-14)

39 items (18 conflict: 5 strong, 13 weak; 21 controls) × 3 conditions × 4 open models (deepseek-v4-flash, qwen3.8-27b, qwen3.5-397b, glm-5.2) × 2 samples. 935 of 936 runs completed (one qwen3.5-397b control run kept failing with 504s). Grader: glm-5.2. Full per-model table: `report.md`.

## Conflict items (strong + weak, all 4 models pooled)

| condition | n | cited both | flagged | orphan asserted | Q1: assumptions incompatible | Q2: rejects orphan |
|---|---|---|---|---|---|---|
| findings:6:all | 144 | 144 | 9 (6%) | 19 (13%) | 123 (85%) | 131 (91%) |
| abstracts:12:all | 144 | 144 | 3 (2%) | 4 (3%) | 135 (94%) | 132 (92%) |
| abstracts:12:optional | 144 | 66 | 5 (3%) | 10 (7%) | 135 (94%) | 131 (91%) |

Strong items: orphan asserted 6/40 (findings), 1/40 (abstracts all), 0/40 (abstracts optional).

## Controls (false alarms)

| condition | n | flagged in paragraph | Q1 says incompatible: control_same | Q1 says incompatible: control_regime |
|---|---|---|---|---|
| findings:6:all | 168 | 1 | 1/96 | 38/72 |
| abstracts:12:all | 167 | 2 | 10/96 | 56/71 |
| abstracts:12:optional | 168 | 1 | 8/96 | 59/72 |

## Reading

- The pilot's headline (orphan asserted in 12/12 Claude runs) does not hold for these open models at this scale: 13% with short findings, 3-7% with abstracts.
- The dominant behavior is unflagged juxtaposition: models cite both sides of a conflict in one paragraph (all 144 runs under "all"), flag it 2-6% of the time, but usually list the findings side by side without drawing the conclusion that needs both. Spot-checked grader notes agree with this reading.
- When asked directly, models see the conflict 85-94% of the time, so the gap is between knowing and saying.
- Full abstracts lower orphan assertion further, consistent with abstracts naming the theory (e.g. "Ricardian equivalence").
- Q1 does not separate conflict items from regime-scopable controls (53-83% of regime controls are called incompatible), as expected: those pairs do clash, just in separable regimes. Q2 does separate them.
- Paragraph flagging has almost no false alarms (4/503 control runs).

## Cost

Eval-model runs: about 13.8 Adaption credits (from logged tokens). Grading tokens were not logged; estimated 8-10 credits.
