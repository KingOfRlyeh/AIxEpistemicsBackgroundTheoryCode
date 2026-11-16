import json,sys,collections
P='/mnt/project-files/pair-finder/eval/run2/'
cols=["cited_both","flagged","orphan_asserted","review_flags_pair","conflict_flags_pair","q1_incompatible","q2_rejects","fresh_q1_incompatible","fresh_q2_rejects"]
def load(f):
    try: return [json.loads(l) for l in open(P+f) if '"score"' in l]
    except FileNotFoundError: return []
rows=[(r,'macro') for r in load('scored.jsonl')]+[(r,'cosmo') for r in load('scored_cosmo.jsonl')]
by=sys.argv[1] if len(sys.argv)>1 else 'pool'
g=collections.defaultdict(list)
for r,f in rows:
    if not r.get('score'): continue
    m=r['model']
    if m=='glm-5.2' and by!='model': continue
    t='conflict' if r['type']=='conflict' else 'control'
    key=(f,r['condition'].split(':')[0],t)+((m,) if by=='model' else ())
    g[key].append(dict(r['score'],cited_both=r.get('cited_both')))
print('key n '+' '.join(c[:12] for c in cols))
for k,xs in sorted(g.items()):
    n=len(xs); print(k,n,' '.join(f"{100*sum(bool(x.get(c)) for x in xs)/n:.0f}" for c in cols))
