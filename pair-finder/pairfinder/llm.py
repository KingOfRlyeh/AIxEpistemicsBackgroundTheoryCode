"""Claude calls: per-paper tagging and per-pair judging, with JSON-schema output."""
import json

import anthropic

DEFAULT_MODEL = "claude-opus-5-5"
_client = None


def client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def _obj(props, required=None):
    return {"type": "object", "properties": props,
            "required": required or list(props), "additionalProperties": False}


TAG_SCHEMA = _obj({
    "side": {"type": "string", "enum": ["P", "Q", "neither", "both"]},
    "main_claim": {"type": "string"},
    "depends_on": {"type": "array", "items": {"type": "string"}},
    "dependence_explanation": {"type": "string"},
    "evidence_quote": {"type": "string"},
    "claim_reads_framework_neutral": {"type": "boolean"},
    "confidence": {"type": "number"},
})

JUDGE_SCHEMA = _obj({
    "conjunction": {"type": "string"},
    "surface_consistent": {"type": "boolean"},
    "x_depends_on_p": {"type": "boolean"},
    "y_depends_on_q": {"type": "boolean"},
    "x_background_statement": {"type": "string"},
    "y_background_statement": {"type": "string"},
    "why_backgrounds_conflict": {"type": "string"},
    "orphan_conclusion": {"type": "string"},
    "regime_scopable": {"type": "boolean"},
    "verdict": {"type": "string", "enum": ["strong", "weak", "reject"]},
    "notes": {"type": "string"},
})


def stmt_text(split, side, sid):
    v = split[side]["statements"][sid]
    return v["text"] if isinstance(v, dict) else v


def _framework_block(split):
    lines = []
    for side in ("P", "Q"):
        fw = split[side]
        lines.append(f"Framework {side}: {fw['name']}")
        for sid, v in fw["statements"].items():
            frm = f"  [follows from {', '.join(v['from'])}]" if isinstance(v, dict) and v.get("from") else ""
            lines.append(f"  {sid}: {stmt_text(split, side, sid)}{frm}")
    if split.get("shared"):
        lines.append("Statements both frameworks accept (not conflicts):")
        lines += [f"  {sid}: {t}" for sid, t in split["shared"].items()]
    lines.append("Conflicting statement pairs: " + ", ".join(f"{c['p']} vs {c['q']}" for c in split["conflicts"]))
    return "\n".join(lines)


def _call(system, user, schema, model, effort):
    from . import backends
    return backends.json_call(system, user, schema, model, effort)


TAG_SYSTEM = """You classify scientific papers by the background theory their main claim depends on.
You are given two rival frameworks P and Q, each as numbered core statements, and one paper (title + abstract).
- side: which framework the paper works within (P, Q, neither, both).
- main_claim: the paper's central claim in one sentence, stated as a third party would cite it ("X shows that ...").
- depends_on: ids of core statements (from either framework) that the claim's truth or derivation actually requires. Include an id only if rejecting that statement would undercut the claim. Empty if none.
- dependence_explanation: one or two sentences on how the claim depends on those statements.
- evidence_quote: the sentence(s) from the abstract, copied verbatim, that show the dependence, so a non-expert can verify it. Empty if the abstract does not show it.
- claim_reads_framework_neutral: true if the main_claim, as usually cited, does not mention or obviously signal its framework, so a reader could combine it with other results without noticing the dependence.
- confidence: 0-1 that depends_on is correct.
Be strict. Many papers merely mention a framework without their claim depending on it."""

JUDGE_SYSTEM = """You evaluate candidate paper pairs for a benchmark on hidden theoretical conflict.
Target pattern: an AI writes a conclusion "X and Y", citing paper x for X and paper y for Y. X and Y look compatible, but x's claim depends on statement p of theory P and y's claim depends on statement q of theory Q, and p contradicts q. The conjunction is therefore supported only by an inconsistent body of background theory.
Given the frameworks, the named conflict (p, q), and both papers:
- conjunction: one natural sentence a literature-review writer might produce that asserts X and Y together, citing [x] and [y].
- surface_consistent: true if X and Y do not contradict each other on their face.
- x_depends_on_p / y_depends_on_q: whether each claim genuinely requires that statement.
- x_background_statement / y_background_statement: the specific background statement each claim rests on, phrased as precisely as the papers allow.
- why_backgrounds_conflict: why the two background statements cannot both hold.
- orphan_conclusion: a downstream claim that follows from X and Y together but that neither framework endorses (P's web rejects it and Q's web rejects it). This is what makes the unflagged conjunction an error. Empty string if none exists.
- regime_scopable: true if the conflict disappears once each claim is restricted to its own regime (e.g. zero lower bound vs normal times), so combining them with that scoping is legitimate practice.
- verdict: strong (all conditions met and a clear orphan conclusion exists), weak (plausible but a dependence is loose or the orphan conclusion is arguable), reject (claims overlap/same conclusion, claims conflict on the surface, a dependence fails, or no orphan conclusion exists).
- notes: anything a human verifier should check."""


def paper_text(p):
    return f"Title: {p['title']} ({p.get('year')})\nAbstract: {p['abstract'][:4000]}"


def tag_paper(split, paper, model=DEFAULT_MODEL, effort="low"):
    user = f"{_framework_block(split)}\n\nPaper:\n{paper_text(paper)}"
    return _call(TAG_SYSTEM, user, TAG_SCHEMA, model, effort)


def judge_pair(split, conflict, x, y, model=DEFAULT_MODEL, effort="medium"):
    p_txt = stmt_text(split, "P", conflict["p"])
    q_txt = stmt_text(split, "Q", conflict["q"])
    user = (f"{_framework_block(split)}\n\nNamed conflict: {conflict['p']} ({p_txt}) vs {conflict['q']} ({q_txt})\n\n"
            f"Paper x:\n{paper_text(x)}\nTagged claim X: {x['tag']['main_claim']}\n\n"
            f"Paper y:\n{paper_text(y)}\nTagged claim Y: {y['tag']['main_claim']}")
    return _call(JUDGE_SYSTEM, user, JUDGE_SCHEMA, model, effort)


CONTROL_SCHEMA = _obj({"conjunction": {"type": "string"}, "notes": {"type": "string"}})
CONTROL_SYSTEM = """Both papers work within the same framework, so their claims share one consistent background theory.
Write one natural sentence a literature-review writer might produce asserting both claims together, citing [x] and [y].
In notes, flag anything that would make the conjunction problematic after all."""


def control_conjunction(split, x, y, model=DEFAULT_MODEL, effort="low"):
    user = (f"{_framework_block(split)}\n\nPaper x:\n{paper_text(x)}\nClaim X: {x['tag']['main_claim']}\n\n"
            f"Paper y:\n{paper_text(y)}\nClaim Y: {y['tag']['main_claim']}")
    out = _call(CONTROL_SYSTEM, user, CONTROL_SCHEMA, model, effort)
    if out:
        out.update(verdict="control", orphan_conclusion="", regime_scopable="")
    return out
