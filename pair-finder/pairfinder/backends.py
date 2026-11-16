"""Model backends. A model id starting with "claude-" goes to the Anthropic API; anything else goes to Adaption.

Adaption (https://docs.adaptionlabs.ai) hosts open models (deepseek-v4-flash, qwen3.8-27b, qwen3.5-397b,
gemma-4-31b-it, gemma-4-26b-a4b-it, glm-5.2, glm-5.3-flash) behind a Responses API. It needs ADAPTION_API_KEY.
Its Responses API documents no JSON-schema output parameter, so JSON calls on Adaption put the schema in the
instructions, parse the reply, check required keys, and retry once.
"""
import json
import re

NO_FALLBACK = {"claude-haiku-5-5"}  # no server-side refusal fallback for Haiku
_clients = {}


def is_claude(model):
    return model.startswith("claude-")


def _anthropic():
    if "anthropic" not in _clients:
        import anthropic
        _clients["anthropic"] = anthropic.Anthropic()
    return _clients["anthropic"]


def _adaption():
    if "adaption" not in _clients:
        from adaption import Adaption
        _clients["adaption"] = Adaption(max_retries=2, timeout=180.0)
    return _clients["adaption"]


def text(model, messages, system=None, max_tokens=4000):
    """Plain text call. messages = [{"role": "user"|"assistant", "content": str}, ...].
    Returns (text, stop_reason, input_tokens, output_tokens)."""
    if is_claude(model):
        kw = dict(model=model, max_tokens=max_tokens, messages=messages)
        if system:
            kw["system"] = system
        if model in NO_FALLBACK:
            resp = _anthropic().messages.create(**kw)
        else:
            resp = _anthropic().beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kw)
        out = "".join(b.text for b in resp.content if b.type == "text")
        return out, resp.stop_reason, resp.usage.input_tokens, resp.usage.output_tokens
    kw = dict(model=model, input=messages, max_output_tokens=max_tokens)
    if system:
        kw["instructions"] = system
    import time
    for attempt in range(12):  # Adaption rate limit says "retry after 60 seconds"
        try:
            resp = _adaption().responses.create(**kw)
            break
        except Exception as e:
            if "429" not in str(e) and "rate_limit" not in str(e) or attempt == 11:
                raise
            time.sleep(60 + 5 * attempt)
    stop = resp.status
    if getattr(resp, "incomplete_details", None) and getattr(resp.incomplete_details, "reason", None):
        stop = resp.incomplete_details.reason
    u = resp.usage
    return resp.output_text or "", stop, (u.input_tokens if u else 0), (u.output_tokens if u else 0)


def _parse_json(s):
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s)
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", s, re.S)
        return json.loads(m.group(0)) if m else None


def json_call(system, user, schema, model, effort="medium", max_tokens=16000):
    """Structured call. Claude: native JSON-schema output. Adaption: schema in the instructions, parsed and checked."""
    if is_claude(model):
        resp = _anthropic().beta.messages.create(
            model=model, max_tokens=max_tokens,
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
            system=system, messages=[{"role": "user", "content": user}],
        )
        if resp.stop_reason in ("refusal", "max_tokens"):
            return None
        t = next((b.text for b in resp.content if b.type == "text"), None)
        return json.loads(t) if t else None
    sys2 = (f"{system}\n\nReply with one JSON object only, no prose and no code fences. "
            f"It must match this JSON schema:\n{json.dumps(schema)}")
    for _ in range(2):
        out, stop, _, _ = text(model, [{"role": "user", "content": user}], system=sys2, max_tokens=max_tokens)
        try:
            obj = _parse_json(out)
        except (json.JSONDecodeError, TypeError):
            obj = None
        if isinstance(obj, dict) and all(k in obj for k in schema.get("required", [])):
            return {k: obj[k] for k in schema["properties"] if k in obj}
    return None
