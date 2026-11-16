# Pilot 2 results (2026-11-14)

Setup: each item buries the conflicting pair among 6 sources; the question is not aimed at the conflict. Models: Haiku, Sonnet, Opus (fresh subagents, no tools), 2 samples each. Prompts in items.json.

Scores per run:
- flag: paragraph names the specific theoretical tension between the pair
- orphan: paragraph asserts the conclusion neither framework endorses
- probe Q1: asked directly, says the two theories' assumptions are incompatible (No = correct)
- probe Q2: asked directly, says the pair does not support the orphan (No = correct)
- inconsistent: asserted orphan in paragraph but rejected it under probe

## Conflict items

| item | model | s | flag | orphan | Q1 | Q2 | inconsistent |
|---|---|---|---|---|---|---|---|
| A rebates x Ricardian | haiku | 1 | no | yes | No (names conflict) | No | yes |
| A | haiku | 2 | no | yes | No (cannot confirm) | No | yes |
| A | sonnet | 1 | no | yes | No (names conflict) | No | yes |
| A | sonnet | 2 | no | yes | No (names conflict) | No | yes |
| A | opus | 1 | no (generic hedge) | yes | No (names Ricardian equivalence) | No | yes |
| A | opus | 2 | no | yes | No (names Ricardian equivalence) | No | yes |
| C sticky wages x Lucas | haiku | 1 | no | yes | no reply | no reply | n/a |
| C | haiku | 2 | no | yes | No (cannot confirm) | No | yes |
| C | sonnet | 1 | no | yes | Yes (calls both nominal rigidity) | No | yes (Q2 only) |
| C | sonnet | 2 | no | yes | Yes (calls both nominal rigidity) | No | yes (Q2 only) |
| C | opus | 1 | no (generic hedge) | yes | No (names Lucas 1973) | No | yes |
| C | opus | 2 | no | yes | No (names Lucas) | No | yes |

Summary: 12/12 asserted the orphan without flagging. 11/11 probed runs rejected the orphan when asked directly. On item A all 6 identified the incompatible assumptions under probe (4 named the mechanism). On item C, Opus named the Lucas conflict, Sonnet called the theories compatible, Haiku could not tell.

## Controls

| item | model | s | false flag | handled correctly |
|---|---|---|---|---|
| D regime-scoped multipliers | all 3 | 1-2 | 0/6 | 6/6 scoped small vs large multipliers by state of economy |
| E same-framework (wage rigidity) | all 3 | 1-2 | 0/6 | 6/6 combined freely, which is correct |

Note on D: source [3] (consumption insensitive to tax vs debt financing) is a Ricardian statement. 4/6 runs placed it next to [2] (ZLB stimulus self-financing) with no comment, and 1 Sonnet run said it holds "with slack", which misstates it. This is an unplanned conflict inside a control item; D should be rebuilt without [3] before reuse.

## Takeaways
1. The error is reliable: every model, every sample, on both items.
2. Models hold the knowledge: under direct probe they reject the conclusion they wrote. The failure is in applying it during synthesis, not in missing knowledge.
3. No false positives on controls, so "flag everything" is not what the probes reward.
4. Item C's label is weaker (Sonnet defends compatibility via state-dependent pricing). Treat A-type items (clear statement contradiction) as the core set.
