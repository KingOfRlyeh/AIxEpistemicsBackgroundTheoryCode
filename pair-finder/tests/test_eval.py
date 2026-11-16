"""Offline test of the eval harness (build -> run -> score -> report) against a local Messages API stub.

Run: python -m tests.test_eval   (from the pair-finder directory)
"""
import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

CALLS = []


class Stub(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        CALLS.append((self.headers.get("anthropic-beta"), body))
        adaption = self.path.endswith("/api/v1/responses")
        if adaption:  # Adaption Responses API: map onto the Messages shape used below
            body = dict(body, system=body.get("instructions", ""), messages=body["input"])
        system = body.get("system", "")
        if "You write eval items" in system:
            text = json.dumps({"question": "how to design support", "dimension": "household response",
                               "probe_q1": "Do [1] and [2] agree?", "probe_q2": "Do [1] and [2] imply Z?"})
        elif "You grade" in system:
            text = json.dumps({"flagged": False, "flag_quote": "", "orphan_asserted": True, "orphan_quote": "Z.",
                               "q1_incompatible": True, "q1_names_conflict": True, "q2_rejects": True,
                               "review_flags_pair": False, "conflict_flags_pair": True, "fresh_q1_incompatible": True,
                               "fresh_q2_rejects": True, "notes": ""})
        else:
            text = "A paragraph [1][2]." if len(body["messages"]) == 1 else "Q1: No. Q2: No."
        if adaption:
            if "JSON schema" in system:
                text = "```json\n" + text + "\n```"  # exercise fence stripping
            msg = {"id": "resp_1", "object": "response", "created_at": 0, "status": "completed", "model": body["model"],
                   "output": [], "output_text": text, "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}}
        else:
            msg = {"id": "msg_1", "type": "message", "role": "assistant", "model": body["model"],
                   "content": [{"type": "text", "text": text}], "stop_reason": "end_turn",
                   "stop_sequence": None, "usage": {"input_tokens": 10, "output_tokens": 5}}
        data = json.dumps(msg).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


def main():
    srv = HTTPServer(("127.0.0.1", 0), Stub)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    os.environ["ANTHROPIC_BASE_URL"] = f"http://127.0.0.1:{srv.server_port}"
    os.environ["ANTHROPIC_API_KEY"] = "test"
    os.environ["ADAPTION_BASE_URL"] = f"http://127.0.0.1:{srv.server_port}"
    os.environ["ADAPTION_API_KEY"] = "test"
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

    from pairfinder import evaluate as ev
    root = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        args = ["--items", str(d / "items.jsonl"), "--runs", str(d / "runs.jsonl"),
                "--scored", str(d / "scored.jsonl"), "--out", str(d / "report.md"), "--samples", "1", "--workers", "2", "--conditions", "findings:6:all,abstracts_anon:12:optional",
                "--models", "claude-haiku-5-5,claude-sonnet-5-5,claude-opus-5-5", "--grader", "claude-opus-5-5", "--model", "claude-opus-5-5"]
        for stage in ["build", "run", "score", "report"]:
            sys.argv = ["x", stage] + args + (["--limit", "2"] if stage == "run" else [])
            ev.main()
        items = [json.loads(l) for l in open(d / "items.jsonl")]
        runs = [json.loads(l) for l in open(d / "runs.jsonl")]
        scored = [json.loads(l) for l in open(d / "scored.jsonl")]
        assert items and all(len(it["distractors"]) >= 4 for it in items)
        assert all(len(r["src"]) == (6 if r["condition"].startswith("findings") else min(12, 2 + len(next(i for i in items if i["id"] == r["item"])["distractors"]))) for r in runs)
        assert all(r["pair"][0] != r["pair"][1] for r in runs)
        assert {it["type"] for it in items} <= {"conflict", "control_same", "control_regime"}
        assert len(runs) == 2 * 2 * 3 and all(r["probe_answer"] == "Q1: No. Q2: No." for r in runs)
        assert all(s["score"]["inconsistent"] for s in scored)
        probe_calls = [b for _, b in CALLS if len(b.get("messages", [])) == 3]
        assert probe_calls and probe_calls[0]["messages"][1]["role"] == "assistant"
        haiku = [(h, b) for h, b in CALLS if b["model"] == "claude-haiku-5-5"]
        assert haiku and all("fallbacks" not in b for _, b in haiku)
        from pairfinder.evaluate import cited
        assert cited("as shown [2, 5] and [7-9]", 8) and cited("x [3]", 3) and not cited("x [13]", 3)
        abs_prompt = [b for _, b in CALLS if len(b.get("messages", [])) == 1 and "abstracts of research" in b["messages"][0]["content"]]
        assert abs_prompt and "Draw on whichever" in abs_prompt[0]["messages"][0]["content"]
        assert all(r["review_answer"] and r["conflict_answer"] and r["fresh_answer"] for r in runs)
        assert len([b for _, b in CALLS if len(b.get("messages", [])) == 7]) == len(runs)  # paragraph + 3 probes
        assert any(s["score"]["conflict_flags_pair"] for s in scored)
        from pairfinder.evaluate import strip_terms
        assert strip_terms("A New Keynesian model with Ricardian agents", "macro_keynesian_vs_new_classical").count("[theory name removed]") == 2
        assert "MOND" not in strip_terms("MOND fits; LCDM does not", "cosmology_dark_matter_vs_mond")
        assert "| conflict" in (d / "report.md").read_text() or "| control_" in (d / "report.md").read_text()
        # Adaption path: open models as subjects and grader, item questions written by an Adaption model
        n0 = len(CALLS)
        a2 = ["--items", str(d / "i2.jsonl"), "--runs", str(d / "r2.jsonl"), "--scored", str(d / "s2.jsonl"),
              "--out", str(d / "rep2.md"), "--samples", "1", "--workers", "2", "--conditions", "findings:6:all",
              "--models", "deepseek-v4-flash,qwen3.8-27b", "--grader", "glm-5.2", "--model", "qwen3.5-397b"]
        for stage in ["build", "run", "score", "report"]:
            sys.argv = ["x", stage] + a2 + (["--limit", "1"] if stage == "run" else [])
            ev.main()
        s2 = [json.loads(l) for l in open(d / "s2.jsonl")]
        assert len(s2) == 2 and all(s["score"] and s["score"]["inconsistent"] for s in s2), s2
        ad = [b for _, b in CALLS[n0:]]
        assert ad and all("input" in b and "messages" not in b for b in ad)
        assert all(b["model"] in ("deepseek-v4-flash", "qwen3.8-27b", "glm-5.2", "qwen3.5-397b") for b in ad)
        probe = [b for b in ad if isinstance(b["input"], list) and len(b["input"]) == 3]
        assert probe and probe[0]["input"][1]["role"] == "assistant"
        assert any("JSON schema" in b.get("instructions", "") for b in ad)
        print(f"OK: {len(items)} items, {len(runs)} runs, {len(scored)} scored, {len(CALLS)} API calls")


if __name__ == "__main__":
    main()
