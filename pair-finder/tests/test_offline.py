"""Offline end-to-end test: fake OpenAlex + a local stub of the Messages API.

Run: python -m tests.test_offline   (from the pair-finder directory)
"""
import json
import os
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

SEEN = []


class Stub(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        SEEN.append((self.headers.get("anthropic-beta"), body))
        user = body["messages"][0]["content"]
        if "same framework" in body["system"]:
            out = {"conjunction": "A [x] and C [y].", "notes": ""}
        elif "Named conflict" in user:
            out = {"conjunction": "A [x] and B [y].", "surface_consistent": True, "x_depends_on_p": True,
                   "y_depends_on_q": True, "x_background_statement": "p", "y_background_statement": "q",
                   "why_backgrounds_conflict": "p and q contradict", "orphan_conclusion": "Z",
                   "regime_scopable": False, "verdict": "strong", "notes": ""}
        else:
            side = "P" if "collapse" in user.split("Paper:")[1].lower() else "Q"
            out = {"side": side, "main_claim": "claim about " + user.split("Title: ")[1][:40],
                   "depends_on": ["P2"] if side == "P" else ["Q3"], "dependence_explanation": "", "evidence_quote": "q",
                   "claim_reads_framework_neutral": True, "confidence": 0.9}
        msg = {"id": "msg_1", "type": "message", "role": "assistant", "model": body["model"],
               "content": [{"type": "text", "text": json.dumps(out)}], "stop_reason": "end_turn",
               "stop_sequence": None, "usage": {"input_tokens": 1, "output_tokens": 1}}
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
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

    from pairfinder import openalex, pipeline as pl

    def fake_search(q, n=20, min_citations=10, extra_filter=""):
        tag = "collapse" if "collapse" in q.lower() or "copenhagen" in q.lower() or "localization" in q.lower() else "bohm"
        return [{"openalex_id": f"W{tag}{q[:5]}{i}", "doi": f"10.0/{tag}{i}", "title": f"{tag} paper {q} {i}",
                 "year": 2000 + i, "cited_by_count": 50, "authors": [], "topic": "",
                 "abstract": f"We study {tag} quantum measurement and particle trajectories in detail. " * 6}
                for i in range(3)]
    openalex.search = fake_search

    splits = pl.load_splits(Path(__file__).resolve().parent.parent / "frameworks.yaml")
    s = splits["qm_collapse_vs_bohm"]
    papers = pl.fetch_split(s, per_query=3)
    assert {p["side"] for p in papers} == {"P", "Q"}, papers
    tagged = pl.tag_split(s, papers, "claude-opus-5-5", workers=4)
    assert all(p["tag"] for p in tagged), [p.get("tag_error") for p in tagged]
    cands = pl.candidate_pairs(s, tagged, top_k=4)
    assert cands and all(c["conflict"] == {"p": "P2", "q": "Q3"} for c in cands), cands
    judged = pl.judge(s, cands, "claude-opus-5-5", workers=4)
    assert all(j["judge"]["verdict"] == "strong" for j in judged), judged
    ctrl = pl.same_framework_controls(s, tagged, top_k=2)
    assert ctrl and all(c["pair_type"].startswith("control_same_") for c in ctrl), ctrl
    cj = pl.judge(s, ctrl, "claude-opus-5-5", workers=2)
    assert all(j["judge"]["verdict"] == "control" for j in cj), cj
    assert pl.anonymize("X holds [Barro 1989] under Ricardian equivalence [Kaur 2019].", {"framework_terms": ["Ricardian equivalence"]}) == "X holds [A] under [framework] [B]."
    raw = pl.raw_pairs(s, papers, top_k=5)
    assert raw and all(r["x"]["side"] == "P" and r["y"]["side"] == "Q" for r in raw)
    with tempfile.TemporaryDirectory() as d:
        pl.write_csv(Path(d) / "p.csv", [pl.flatten("qm", s, j) for j in judged])
        print((Path(d) / "p.csv").read_text().splitlines()[1][:200])
    beta, body = SEEN[0]
    assert "server-side-fallback" in (beta or ""), beta
    assert body["output_config"]["format"]["type"] == "json_schema" and body["fallbacks"] == "default"
    print(f"OK: {len(papers)} papers, {len(tagged)} tagged, {len(cands)} pairs, {len(SEEN)} API calls")


if __name__ == "__main__":
    main()
