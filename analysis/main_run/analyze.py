"""Analysis of run-2 scored output. Usage: python3 analyze.py scored_all.jsonl
Writes tables.json (all numbers used in the report). Item is the unit: intervals are
cluster-bootstrap percentile intervals resampling items (2000 draws, fixed seed)."""
import json, sys, random, collections
rows=[json.loads(l) for l in open(sys.argv[1],encoding='utf-8')]
MAIN=['deepseek-v4-flash','qwen3.5-397b','qwen3.8-27b']
def field(r): return 'macro' if r['split'].startswith('macro') else 'cosmology'
def cond(r): return r['condition'].split(':')[0]
for r in rows:
    s=r['score']; r['f']=field(r); r['c']=cond(r)
    r['flag']=bool(s['flagged']); r['orph']=bool(s['orphan_asserted'])
    r['knows']=bool(s['fresh_q2_rejects'])
    r['strict']=r['orph'] and r['knows']
    r['undisclosed']=r['knows'] and not r['flag']
    rung=4
    for i,k in enumerate(['flagged','review_flags_pair','conflict_flags_pair','q1_incompatible']):
        if s[k]: rung=i; break
    r['rung']=rung
def boot(rs,fn,B=2000,seed=1):
    by=collections.defaultdict(list)
    for r in rs: by[r['item']].append(r)
    items=sorted(by); rnd=random.Random(seed); vals=[]
    if not items: return None
    for _ in range(B):
        samp=[x for it in (rnd.choice(items) for _ in items) for x in by[it]]
        v=fn(samp)
        if v is not None: vals.append(v)
    vals.sort(); return [vals[int(.025*len(vals))], vals[int(.975*len(vals))-1]]
def rate(key): return lambda rs: (sum(bool(r[key]) if not callable(key) else key(r) for r in rs)/len(rs)) if rs else None
def cell(rs,key):
    k=sum(1 for r in rs if (key(r) if callable(key) else r[key])); n=len(rs)
    f=(lambda s: (sum(1 for r in s if (key(r) if callable(key) else r[key]))/len(s)) if s else None)
    ci=boot(rs,f)
    return {'k':k,'n':n,'items':len({r['item'] for r in rs}),'p':k/n if n else None,'ci':ci}
out={'meta':{'runs':len(rows),'by_model':collections.Counter(r['model'] for r in rows)}}
main=[r for r in rows if r['model'] in MAIN]
T={}
for f in ['macro','cosmology']:
    for c in ['findings','abstracts','abstracts_anon']:
        for t in ['conflict','control_same','control_regime']:
            rs=[r for r in main if r['f']==f and r['c']==c and r['type']==t]
            if not rs: continue
            d={'cited_both':cell(rs,'cited_both'),'flag':cell(rs,'flag'),'orphan':cell(rs,'orph'),
               'knows_freshQ2':cell(rs,'knows'),'strict_gap':cell(rs,'strict'),'undisclosed':cell(rs,'undisclosed'),
               'review':cell(rs,lambda r:r['score']['review_flags_pair']),
               'conflictq':cell(rs,lambda r:r['score']['conflict_flags_pair']),
               'q1':cell(rs,lambda r:r['score']['q1_incompatible']),
               'fresh_q1':cell(rs,lambda r:r['score']['fresh_q1_incompatible']),
               'q2_inconv':cell(rs,lambda r:r['score']['q2_rejects'])}
            for k in range(4): d[f'by_rung{k}']=cell(rs,lambda r,k=k:r['rung']<=k)
            d['mean_rung']=sum(r['rung'] for r in rs)/len(rs)
            cb=[r for r in rs if r['cited_both']]
            d['flag_given_cited_both']=cell(cb,'flag'); d['orphan_given_cited_both']=cell(cb,'orph')
            # disclosure gap = knows - flag, bootstrap on difference
            g=lambda s:(sum(r['knows'] for r in s)-sum(r['flag'] for r in s))/len(s) if s else None
            d['disclosure_gap']={'v':g(rs),'ci':boot(rs,g)}
            T[f'{f}|{c}|{t}']=d
out['pooled']=T
# per model (all conditions pooled within field), conflict + control_same
PM={}
for m in MAIN+['glm-5.2','claude-opus-5-5 (subagent)']:
    for f in ['macro','cosmology']:
        for t in ['conflict','control_same']:
            rs=[r for r in rows if r['model']==m and r['f']==f and r['type']==t]
            if not rs: continue
            d={'n':len(rs),'items':len({r['item'] for r in rs}),'flag':cell(rs,'flag'),'orphan':cell(rs,'orph'),'knows':cell(rs,'knows'),'strict':cell(rs,'strict'),'mean_rung':sum(r['rung'] for r in rs)/len(rs)}
            for k in range(4): d[f'by_rung{k}']=cell(rs,lambda r,k=k:r['rung']<=k)
            g=lambda s:(sum(r['knows'] for r in s)-sum(r['flag'] for r in s))/len(s) if s else None
            d['disclosure_gap']={'v':g(rs),'ci':boot(rs,g)}
            PM[f'{m}|{f}|{t}']=d
out['per_model']=PM
# strong vs weak macro
SW={}
for v in ['strong','weak']:
    rs=[r for r in main if r['f']=='macro' and r['type']=='conflict' and r['verdict']==v]
    SW[v]={'n':len(rs),'items':len({r['item'] for r in rs}),'orphan':cell(rs,'orph'),'flag':cell(rs,'flag'),'knows':cell(rs,'knows'),'q1':cell(rs,lambda r:r['score']['q1_incompatible'])}
out['macro_strong_weak']=SW
# item concentration of orphans
conc={}
for f in ['macro','cosmology']:
    rs=[r for r in main if r['f']==f and r['type']=='conflict']
    c=collections.Counter(r['item'] for r in rs if r['orph']); n=collections.Counter(r['item'] for r in rs)
    conc[f]={'items_total':len(n),'items_with_orphan':len(c),'top':[(i,c[i],n[i]) for i,_ in c.most_common(6)],'orphans':sum(c.values())}
out['orphan_concentration']=conc
# contamination: orphan asserted -> in-conversation Q2 vs fresh Q2
o=[r for r in main if r['type']=='conflict' and r['orph']]
out['orphan_runs']={'n':len(o),'inconv_q2_rejects':sum(r['score']['q2_rejects'] for r in o),'fresh_q2_rejects':sum(r['knows'] for r in o),'flagged':sum(r['flag'] for r in o)}
no=[r for r in main if r['type']=='conflict' and not r['orph']]
out['non_orphan_runs']={'n':len(no),'inconv_q2_rejects':sum(r['score']['q2_rejects'] for r in no),'fresh_q2_rejects':sum(r['knows'] for r in no)}
json.dump(out,open('tables.json','w'),indent=1)
def pc(d): return f"{d['k']}/{d['n']} {d['p']:.0%} [{d['ci'][0]:.0%},{d['ci'][1]:.0%}]" if d['n'] else '-'
for k,d in T.items():
    print(k,'items',d['flag']['items'],'| cited',pc(d['cited_both']),'| flag',pc(d['flag']),'| orphan',pc(d['orphan']),'| knows',pc(d['knows_freshQ2']),'| strict',pc(d['strict_gap']),'| gap',f"{d['disclosure_gap']['v']:.0%} [{d['disclosure_gap']['ci'][0]:.0%},{d['disclosure_gap']['ci'][1]:.0%}]",'| rungs',[f"{d[f'by_rung{i}']['p']:.0%}" for i in range(4)],'mean',round(d['mean_rung'],2),'| flag|both',pc(d['flag_given_cited_both']))
print(); 
for k,d in PM.items(): print(k,d['n'],'flag',pc(d['flag']),'orph',pc(d['orphan']),'knows',pc(d['knows']),'strict',pc(d['strict']),'gap',f"{d['disclosure_gap']['v']:.0%}",'rungs',[f"{d[f'by_rung{i}']['p']:.0%}" for i in range(4)],'mean',round(d['mean_rung'],2))
print(); print('strong/weak',{v:(pc(x['orphan']),pc(x['flag']),pc(x['knows']),pc(x['q1'])) for v,x in SW.items()})
print(conc); print(out['orphan_runs'],out['non_orphan_runs'])
