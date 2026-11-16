# Controlled experiment: results

Two hand-built items, four models (gemma-4-31b-it, deepseek-v4-flash, qwen3.5-397b, glm-5.2), 8 conditions, 5 samples each: 320 briefs, plus 96 fresh-conversation belief probes (416 calls, none empty). Models were called through the Adaption API with no system prompt, and source order was shuffled per sample.

- **Item A:** tax rebates (Johnson, Parker & Souleles 2006) versus Ricardian equivalence (Barro 1989); same-theory control from Parker et al. 2013.
- **Item C:** kin selection (Hughes et al. 2008) versus standard natural selection (Nowak et al. 2010); same-theory control from Cornwallis et al. 2010.

Every source has a hedged version that keeps its scope conditions and a one-line version that drops them. The sources, question, and prompt are otherwise the same, except in the cite-all condition, which used a different prompt (a report paragraph with no recommendation).

## Item A: briefs asserting the orphan conclusion

Orphan conclusion: "Debt-financed tax rebates raise household spending without reducing national saving."

| Condition | Orphan asserted | By model (gemma, deepseek, qwen, glm) |
|---|---|---|
| Both rivals, hedged text | 0 of 20 | 0, 0, 0, 0 |
| Both rivals, one-line text | 19 of 20 | 5, 5, 4, 5 |
| Both rivals, hedged, cite every source (different prompt) | 0 of 20 | 0, 0, 0, 0 |
| Rival pair alone, hedged | 0 of 20 | 0, 0, 0, 0 |
| Rebate source removed | 0 of 20 | |
| Ricardian source removed | 0 of 20 | |
| Same-theory control (hedged and one-line) | 0 of 40 | |

## Item A: what the models said about the conclusion

| Setting | Result |
|---|---|
| Same conversation, after a one-line brief: Q2 "the two sources support the conclusion" | 15 of 20 |
| Same conversation, after a one-line brief: Q1 "the sources' assumptions cannot both hold" | 19 of 20 |
| Same conversation: both of the above in one run | 14 of 20 |
| Fresh conversation, no sources: endorses the orphan conclusion | 0 of 24 |
| Fresh conversation, no sources: endorses the control statement | 23 of 24 |

The fresh-conversation probes are separate runs, so the last two rows compare conditions and are not a reversal within one run.

## Item C

1 orphan conclusion in 40 conflict briefs. The two sources state opposite causal claims in plain words, and models presented the pair as a debate or used one side only. Fresh-conversation probes: 0 of 24 endorsed the orphan statement and 22 of 24 endorsed the control statement.

## Limits

- One item carries the result; item C shows nothing either way.
- Briefs were coded by one LLM reader (Claude), not blind. Probe answers were parsed from the opening Yes or No.
- Source texts paraphrase the papers' abstracts. The one-line Ricardian sentence is blunter than the paper, which is the manipulation.
- The cite-all condition changed the prompt as well as the citation instruction, so it does not isolate the effect of that instruction.
- Wilson intervals are on runs within one item.

## Files

| File | Contents |
|---|---|
| `items_v2.json` | Sources (hedged and one-line), questions, prompts, follow-up questions, belief-probe statements |
| `run_pretest.py` | Runner (Adaption, Anthropic, or OpenAI-compatible APIs); writes `results.jsonl` |
| `results.jsonl` | Every prompt and response (416 calls) |
| `score_and_report.py` | Regenerates the files below from `results.jsonl` |
| `codes.json` | Per-brief codes |
| `pretest_tables.json` | All counts |
| `figure2_controlled_experiment.png` | Figure 2 in the paper |
| `pretest_browser.html` | All 320 briefs with prompts, follow-up answers and codes; open in a browser |
| `superseded/` | Earlier write-up and figure script, kept for the record |

The files keep the working name "pretest"; the paper calls this the controlled experiment.
