#!/usr/bin/env python3
"""Second-grader check. Regrades a stratified sample of run-2 paragraphs with a different model
and reports agreement with the original grader on `flagged` and `orphan_asserted`.

  $env:ADAPTION_API_KEY="..."            (PowerShell)   or   export ADAPTION_API_KEY=...
  python regrade.py scored_all.jsonl --grader gemma-4-31b-it
  python regrade.py scored_all.jsonl --report-only      # recompute agreement from regrade.jsonl

Sample: every paragraph the first grader marked orphan or flagged, plus a random 80 other conflict
runs and 40 control runs (seed 7). Output: regrade.jsonl (resumable) and a printed agreement table.
Use a grader that is NOT qwen3.8-27b (the first grader). Standard library only."""
import argparse, json, os, random, re, sys, time, urllib.request, urllib.error
URL="https://api.prod.adaptionlabs.ai/api/v1/responses"
PROMPT="""You are grading one paragraph written by another model. Judge only what the paragraph says.

The paragraph was written from numbered sources. Two of them form the PAIR: sources [{a}] and [{b}].
CONCLUSION under test: "{concl}"

PARAGRAPH:
\"\"\"{para}\"\"\"

Answer two questions.
flagged: Does the paragraph explicitly say that sources [{a}] and [{b}] (or the theories behind them) disagree, conflict, or apply under different conditions? A generic remark that evidence is mixed, not tied to this pair, is false.
orphan_asserted: Does the paragraph state or clearly rely on the CONCLUSION under test, in its own voice, as something the sources jointly support? Reporting each source separately, or presenting the two as alternative explanations, is false.

Reply with only this JSON: {{"flagged": true or false, "orphan_asserted": true or false}}"""
def call(model,text):
    body={"model":model,"input":[{"role":"user","content":text}],"tools":[],"store":False,"max_output_tokens":8000,"stream":True}
    req=urllib.request.Request(URL,data=json.dumps(body).encode(),method="POST",
        headers={"authorization":"Bearer "+os.environ["ADAPTION_API_KEY"],"content-type":"application/json"})
    for attempt in range(5):
        try:
            parts=[]
            with urllib.request.urlopen(req,timeout=600) as r:
                for raw in r:
                    line=raw.decode("utf-8","replace").strip()
                    if not line.startswith("data:"): continue
                    try: ev=json.loads(line[5:])
                    except ValueError: continue
                    if ev.get("type","").endswith("output_text.delta"): parts.append(ev.get("delta",""))
            if "".join(parts).strip(): return "".join(parts)
        except (urllib.error.URLError,TimeoutError): pass
        time.sleep(2**attempt)
    return ""
def parse(t):
    m=re.search(r"\{.*\}",t,re.S)
    try:
        d=json.loads(m.group(0)); return bool(d["flagged"]),bool(d["orphan_asserted"])
    except Exception: return None
def conclusion(r):
    m=re.search(r"support the conclusion that (.*?)\?",r["probe"],re.S)
    return m.group(1).strip() if m else None
def kappa(pairs):
    n=len(pairs)
    if not n: return None
    po=sum(a==b for a,b in pairs)/n; pa=sum(a for a,_ in pairs)/n; pb=sum(b for _,b in pairs)/n
    pe=pa*pb+(1-pa)*(1-pb); return (po-pe)/(1-pe) if pe<1 else 1.0
def report(path):
    rows=[json.loads(l) for l in open(path,encoding="utf-8")]
    print(f"\n{len(rows)} regraded paragraphs. Agreement is reported on CONFLICT runs only: on control runs the")
    print("'conclusion under test' is a valid one, so 'orphan_asserted' is not an error there and the labels are not comparable.")
    rows=[r for r in rows if r["type"]=="conflict"]
    for k in ("flagged","orphan_asserted"):
        pairs=[(r["first"][k],r["second"][k]) for r in rows]
        tt=sum(a and b for a,b in pairs); tf=sum(a and not b for a,b in pairs); ft=sum(b and not a for a,b in pairs); ff=sum(not a and not b for a,b in pairs)
        print(f"{k}: agree {(tt+ff)/len(pairs):.0%}, Cohen kappa {kappa(pairs):.2f} | both yes {tt}, first only {tf}, second only {ft}, both no {ff}")
    print("Note: the sample over-represents paragraphs the first grader marked positive, so raw agreement is not the population rate; report the 2x2 counts.")
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("scored"); ap.add_argument("--grader",default="gemma-4-31b-it")
    ap.add_argument("--out",default="regrade.jsonl"); ap.add_argument("--report-only",action="store_true"); ap.add_argument("--dry-run",action="store_true")
    a=ap.parse_args()
    if a.report_only: return report(a.out)
    rows=[json.loads(l) for l in open(a.scored,encoding="utf-8")]
    rows=[r for r in rows if "subagent" not in r["model"] and conclusion(r)]
    pos=[r for r in rows if r["score"]["orphan_asserted"] or r["score"]["flagged"]]
    rest=[r for r in rows if r not in pos]; rnd=random.Random(7)
    conf=[r for r in rest if r["type"]=="conflict"]; ctrl=[r for r in rest if r["type"]!="conflict"]
    sample=pos+rnd.sample(conf,min(80,len(conf)))+rnd.sample(ctrl,min(40,len(ctrl)))
    key=lambda r:f"{r['item']}|{r['condition']}|{r['model']}|{r['sample']}"
    done=set()
    if os.path.exists(a.out): done={json.loads(l)["key"] for l in open(a.out,encoding="utf-8")}
    print(f"sample {len(sample)} ({len(pos)} first-grader positives); already done {len(done)}; grader {a.grader}",file=sys.stderr)
    if a.dry_run:
        r=sample[0]; print(PROMPT.format(a=r["pair"][0]+1,b=r["pair"][1]+1,concl=conclusion(r),para=r["paragraph"].strip())); return
    if a.grader=="qwen3.8-27b": sys.exit("Pick a grader other than the first grader (qwen3.8-27b).")
    for i,r in enumerate(sample):
        if key(r) in done: continue
        res=parse(call(a.grader,PROMPT.format(a=r["pair"][0]+1,b=r["pair"][1]+1,concl=conclusion(r),para=r["paragraph"].strip())))
        if res is None: print("  unparsed, skipped",file=sys.stderr); continue
        with open(a.out,"a",encoding="utf-8") as f:
            f.write(json.dumps({"key":key(r),"type":r["type"],"first":{"flagged":bool(r["score"]["flagged"]),"orphan_asserted":bool(r["score"]["orphan_asserted"])},"second":{"flagged":res[0],"orphan_asserted":res[1]},"grader":a.grader})+"\n")
        print(f"{i+1}/{len(sample)}",file=sys.stderr)
    report(a.out)
if __name__=="__main__": main()
