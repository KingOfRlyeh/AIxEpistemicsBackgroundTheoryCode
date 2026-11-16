import json,sys,collections
scored,regr=sys.argv[1],sys.argv[2]
MAIN=['deepseek-v4-flash','qwen3.5-397b','qwen3.8-27b']
rows=[json.loads(l) for l in open(scored)]
key=lambda r:f"{r['item']}|{r['condition']}|{r['model']}|{r['sample']}"
byk={key(r):r for r in rows}
G=[json.loads(l) for l in open(regr)]
for g in G:
    r=byk[g['key']]; g['f']='macro' if r['split'].startswith('macro') else 'cosmology'; g['model']=r['model']; g['c']=r['condition'].split(':')[0]
def kappa(p):
    n=len(p); po=sum(a==b for a,b in p)/n; pa=sum(a for a,_ in p)/n; pb=sum(b for _,b in p)/n
    pe=pa*pb+(1-pa)*(1-pb); return (po-pe)/(1-pe) if pe<1 else float('nan')
print(f"regraded {len(G)}")
for lab in ('flagged','orphan_asserted'):
    for name,sub in [('all',G)]+[(f"{f}/{t}",[g for g in G if g['f']==f and (g['type']=='conflict')==(t=='conflict')]) for f in ('macro','cosmology') for t in ('conflict','control')]:
        p=[(g['first'][lab],g['second'][lab]) for g in sub]
        if not p: continue
        c=collections.Counter(p)
        print(f"{lab:16s} {name:20s} n={len(p):3d} qY/gY {c[(True,True)]:3d} qY/gN {c[(True,False)]:3d} qN/gY {c[(False,True)]:3d} qN/gN {c[(False,False)]:3d} kappa {kappa(p):.2f}")
# headline: conflict, 3 main models, by field. Estimate gemma rate = gemma-yes among qwen-positives (all regraded) + qwen-negatives * gemma-yes rate on sampled negatives
print("\nHeadline (conflict, 3 main models). qwen-positive = flagged or orphan per qwen; all regraded. Negatives sampled.")
pos=lambda r:bool(r['score']['flagged']) or bool(r['score']['orphan_asserted'])
gk={g['key']:g for g in G}
for f in ('macro','cosmology'):
  for cond in (None,'findings','abstracts','abstracts_anon'):
    pop=[r for r in rows if r['model'] in MAIN and r['type']=='conflict' and r['split'].startswith('macro')==(f=='macro') and (cond is None or r['condition'].split(':')[0]==cond)]
    P=[r for r in pop if pos(r)]; N=[r for r in pop if not pos(r)]
    Ns=[gk[key(r)] for r in N if key(r) in gk]
    out=[]
    for lab in ('flagged','orphan_asserted'):
        q=sum(bool(r['score'][lab]) for r in pop)
        gp=sum(gk[key(r)]['second'][lab] for r in P if key(r) in gk)
        miss=sum(1 for r in P if key(r) not in gk)
        ns=sum(g['second'][lab] for g in Ns); est=gp+(ns/len(Ns)*len(N) if Ns else 0)
        out.append(f"{lab}: qwen {q}/{len(pop)} ({q/len(pop):.0%}) gemma ~{est:.1f}/{len(pop)} ({est/len(pop):.0%}) [pos missing {miss}; neg sampled {len(Ns)}/{len(N)}, gemma-yes {ns}]")
    print(f,cond or 'ALL',' | '.join(out))
