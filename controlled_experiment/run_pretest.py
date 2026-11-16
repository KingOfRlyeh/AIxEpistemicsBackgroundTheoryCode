#!/usr/bin/env python3
"""Pre-test runner for the orphan-conclusion eval.

Usage
  # 1. See every prompt without calling anything:
  python3 run_pretest.py --items items_v2.json --dry-run

  # 1b. Run against the Adaption API (hosted open-weight models):
  export ADAPTION_API_KEY=...
  python3 run_pretest.py --items items_v2.json --provider adaption \
      --models qwen3.5-397b glm-5.2 gemma-4-31b-it --samples 5

  # 2. Run against the Anthropic API (no system prompt, default temperature):
  export ANTHROPIC_API_KEY=...
  python3 run_pretest.py --items items_v2.json --provider anthropic \
      --models claude-haiku-5-5 claude-sonnet-5-5 --samples 5

  # 3. Run against any OpenAI-compatible endpoint:
  export OPENAI_API_KEY=...        # or the key for that provider
  python3 run_pretest.py --items items_v2.json --provider openai \
      --base-url https://api.openai.com/v1 --models <model-id> --samples 5

Output: results.jsonl (one line per call, resumable) and prompts_preview.txt.
Only the standard library is used.
"""
import argparse, hashlib, json, os, random, sys, time, urllib.request, urllib.error

PRETEST_ITEMS = ["A_rebates_ricardian", "C_eusociality"]

# cell name -> (pack, text field, prompt kind, run in-context probes afterwards?)
CELLS = {
    "conflict_kept":      ("conflict",               "text",          "recommend", True),
    "conflict_stripped":  ("conflict",               "text_stripped", "recommend", True),
    "control_kept":       ("control_same_framework", "text",          "recommend", True),
    "control_stripped":   ("control_same_framework", "text_stripped", "recommend", True),
    "ablate_minus_p":     ("ablation_minus_p",       "text",          "recommend", False),
    "ablate_minus_q":     ("ablation_minus_q",       "text",          "recommend", False),
    "easy_pair_alone":    ("easy_pair_alone",        "text",          "recommend", False),
    "conflict_cite_all":  ("conflict",               "text",          "cite_all",  False),
}


LAST = {}
STREAM = True


def _read_stream(r):
    """Read a server-sent-event stream from the Responses API and return the full text.
    Streaming keeps the connection alive while a reasoning model thinks, which avoids gateway timeouts."""
    parts, final = [], None
    for raw in r:
        line = raw.decode("utf-8", errors="replace").strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload in ("", "[DONE]"):
            continue
        try:
            ev = json.loads(payload)
        except ValueError:
            continue
        t = ev.get("type", "")
        if t.endswith("output_text.delta"):
            parts.append(ev.get("delta", ""))
        elif t in ("response.completed", "response.incomplete", "response.failed"):
            final = ev.get("response", {})
        elif t == "error":
            raise RuntimeError("stream error: " + json.dumps(ev)[:300])
    text = "".join(parts)
    if final:
        LAST["status"] = final.get("status"); LAST["incomplete"] = final.get("incomplete_details"); LAST["usage"] = final.get("usage")
        if not text:
            text = final.get("output_text") or "".join(
                p.get("text", "") for it in final.get("output", []) if it.get("type") == "message"
                for p in it.get("content", []) if p.get("type") == "output_text")
    return text


class EmptyResponse(Exception):
    pass


def call_model(provider, base_url, model, messages, max_tokens=600):
    """Retries when the model returns no text (common when a reasoning model spends its budget thinking)."""
    for attempt in range(3):
        text = _call_once(provider, base_url, model, messages, max_tokens * (attempt + 1))
        if text and text.strip():
            return text
        print(f"   empty reply from {model} (status={LAST.get('status')}, detail={LAST.get('incomplete')}, usage={LAST.get('usage')}); retrying", file=sys.stderr)
    raise EmptyResponse(model)


def _call_once(provider, base_url, model, messages, max_tokens=600):
    if provider == "adaption":
        # Adaption Responses API. tools=[] keeps tools off; no stack, so no memory is added.
        url = (base_url or "https://api.prod.adaptionlabs.ai/api/v1") + "/responses"
        headers = {"authorization": "Bearer " + os.environ["ADAPTION_API_KEY"],
                   "content-type": "application/json"}
        body = {"model": model, "input": messages, "tools": [], "store": False,
                "max_output_tokens": max(max_tokens * 10, 8000), "stream": STREAM}
    elif provider == "anthropic":
        url = (base_url or "https://api.anthropic.com") + "/v1/messages"
        headers = {"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                   "anthropic-version": "2023-06-01", "content-type": "application/json"}
        body = {"model": model, "max_tokens": max_tokens, "messages": messages}
    else:
        url = (base_url or "https://api.openai.com/v1") + "/chat/completions"
        headers = {"authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
                   "content-type": "application/json"}
        body = {"model": model, "max_tokens": max_tokens, "messages": messages}
    data = json.dumps(body).encode()
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=600) as r:
                if provider == "adaption" and STREAM:
                    return _read_stream(r)
                out = json.loads(r.read())
            if provider == "adaption":
                LAST["status"] = out.get("status"); LAST["incomplete"] = out.get("incomplete_details"); LAST["usage"] = out.get("usage")
                if out.get("output_text"):
                    return out["output_text"]
                return "".join(p.get("text", "") for it in out.get("output", [])
                               if it.get("type") == "message"
                               for p in it.get("content", []) if p.get("type") == "output_text")
            if provider == "anthropic":
                return "".join(b.get("text", "") for b in out["content"])
            return out["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            if e.code in (408, 429, 500, 502, 503, 504, 524, 529):
                time.sleep(2 ** attempt + random.random())
                continue
            raise RuntimeError(f"HTTP {e.code}: {e.read().decode()[:300]}")
        except (urllib.error.URLError, TimeoutError):
            time.sleep(2 ** attempt)
    raise RuntimeError("gave up after retries (timeouts or server errors)")


def build_brief(d, item, cell, sample):
    pack_name, field, kind, _ = CELLS[cell]
    ids = list(item["packs"][pack_name])
    # deterministic shuffle per (item, cell, sample) so runs are reproducible
    seed = int(hashlib.sha256(f"{item['id']}|{cell}|{sample}".encode()).hexdigest(), 16) % 2**32
    random.Random(seed).shuffle(ids)
    lines = [f"[{i+1}] {d['sources'][sid][field]}" for i, sid in enumerate(ids)]
    if kind == "cite_all":
        tmpl = d["prompts"]["brief_cite_all_arm"]
    else:
        tmpl = d["prompts"]["brief_recommendation"][0]
    prompt = tmpl.format(question=item["question"], sources="\n".join(lines))
    return prompt, ids


def pair_for(item, cell):
    pack_name = CELLS[cell][0]
    if pack_name == "conflict":
        return item["pair"], item["orphan_statement"]
    c = item["control_same_framework"]
    return c["pair"], c["valid_joint_statement"]


def jobs(d, models, samples, probe_repeats):
    for model in models:
        for item in d["items"]:
            if item["id"] not in PRETEST_ITEMS:
                continue
            for cell in CELLS:
                for s in range(samples):
                    yield {"kind": "brief", "model": model, "item": item["id"], "cell": cell, "sample": s}
            stmts = {"orphan": item["orphan_statement"],
                     "control_valid": item["control_same_framework"]["valid_joint_statement"]}
            for sname in stmts:
                for pol in ("positive", "negative"):
                    for s in range(probe_repeats):
                        yield {"kind": "belief", "model": model, "item": item["id"],
                               "statement": sname, "polarity": pol, "sample": s}


def key(j):
    return json.dumps({k: j[k] for k in sorted(j) if k in
                       ("kind", "model", "item", "cell", "sample", "statement", "polarity")})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", default="items_v2.json")
    ap.add_argument("--provider", choices=["adaption", "anthropic", "openai"], default="adaption")
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--models", nargs="+", default=["MODEL"])
    ap.add_argument("--samples", type=int, default=5)
    ap.add_argument("--probe-repeats", type=int, default=3)
    ap.add_argument("--out", default="results.jsonl")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-stream", action="store_true", help="turn off streaming for the Adaption API")
    a = ap.parse_args()
    global STREAM
    STREAM = not a.no_stream

    keyvar = {"adaption": "ADAPTION_API_KEY", "anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}[a.provider]
    if not a.dry_run and not os.environ.get(keyvar):
        sys.exit(f"{keyvar} is not set. In PowerShell:  $env:{keyvar}=\"your_key\"   (then rerun in the same window)")
    print(f"provider: {a.provider}", file=sys.stderr)
    d = json.load(open(a.items, encoding="utf-8"))
    items = {it["id"]: it for it in d["items"]}
    done = set()
    if os.path.exists(a.out) and not a.dry_run:
        good = []
        for line in open(a.out, encoding="utf-8"):
            r = json.loads(line)
            ok = bool((r.get("response") or "").strip())
            if "probe_q1" in r:
                ok = ok and bool(r["probe_q1"].strip()) and bool((r.get("probe_q2") or "").strip())
            if ok:
                good.append(line if line.endswith("\n") else line + "\n")
                done.add(key(r))
        with open(a.out, "w", encoding="utf-8") as f:
            f.writelines(good)
        print(f"kept {len(good)} complete rows from {a.out}; incomplete rows will be rerun", file=sys.stderr)

    if a.models == ["MODEL"] and not a.dry_run:
        sys.exit("Pass --models, e.g. --models qwen3.5-397b glm-5.2")
    preview = open("prompts_preview.txt", "w", encoding="utf-8") if a.dry_run else None
    n = 0
    skipped = 0
    for j in jobs(d, a.models, a.samples, a.probe_repeats):
        if key(j) in done:
            continue
        item = items[j["item"]]
        try:
            j = run_job(d, item, j, a, preview)
        except RuntimeError as e:
            skipped += 1
            print(f"   SKIPPED (API error: {str(e)[:160]}): {j['model']} {j['item']} {j.get('cell') or j.get('statement')}", file=sys.stderr)
            continue
        except EmptyResponse:
            skipped += 1
            print(f"   SKIPPED (still empty): {j['model']} {j['item']} {j.get('cell') or j.get('statement')}", file=sys.stderr)
            continue
        if j is None:
            n += 1
            continue
        j["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        with open(a.out, "a", encoding="utf-8") as f:
            f.write(json.dumps(j, ensure_ascii=False) + "\n")
        n += 1
        print(f"{n}: {j['model']} {j['item']} {j.get('cell') or j['statement'] + '/' + j['polarity']} s{j['sample']}", file=sys.stderr)
    if a.dry_run:
        preview.close()
        print(f"dry run: {n} conversations per the settings given; prompts written to prompts_preview.txt")
    elif skipped:
        print(f"{skipped} calls failed or returned no text after retries. Rerun the same command to try them again.")


def run_job(d, item, j, a, preview):
    """Returns the finished job dict, or None in dry-run mode."""
    if True:
        if j["kind"] == "brief":
            prompt, order = build_brief(d, item, j["cell"], j["sample"])
            j["source_order"] = order
            j["prompt"] = prompt
            if a.dry_run:
                if j["sample"] == 0 and j["model"] == a.models[0]:
                    preview.write(f"===== {j['item']} | {j['cell']} =====\n{prompt}\n\n")
                return None
            msgs = [{"role": "user", "content": prompt}]
            j["response"] = call_model(a.provider, a.base_url, j["model"], msgs)
            if CELLS[j["cell"]][3]:  # in-context probes, same conversation
                pair, stmt = pair_for(item, j["cell"])
                ia, ib = order.index(pair[0]) + 1, order.index(pair[1]) + 1
                p = d["prompts"]["in_context_probe"]
                msgs.append({"role": "assistant", "content": j["response"]})
                q1 = p["q1"].format(a=ia, b=ib)
                msgs.append({"role": "user", "content": q1})
                j["probe_q1"] = call_model(a.provider, a.base_url, j["model"], msgs, 200)
                # q2 asked from the post-brief state, not after q1, to avoid order effects
                msgs2 = msgs[:2] + [{"role": "user", "content": p["q2"].format(a=ia, b=ib, statement=stmt)}]
                j["probe_q2"] = call_model(a.provider, a.base_url, j["model"], msgs2, 200)
                j["pair_citation_numbers"] = [ia, ib]
        else:
            stmt = (item["orphan_statement"] if j["statement"] == "orphan"
                    else item["control_same_framework"]["valid_joint_statement"])
            prompt = d["prompts"]["belief_probe_fresh_context"][j["polarity"]].format(statement=stmt)
            j["prompt"] = prompt
            if a.dry_run:
                if j["sample"] == 0 and j["model"] == a.models[0]:
                    preview.write(f"===== {j['item']} | belief | {j['statement']} | {j['polarity']} =====\n{prompt}\n\n")
                return None
            j["response"] = call_model(a.provider, a.base_url, j["model"],
                                       [{"role": "user", "content": prompt}], 120)
        return j


if __name__ == "__main__":
    main()
