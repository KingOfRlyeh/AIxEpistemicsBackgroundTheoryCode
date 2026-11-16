"""Scores the 5-sample pre-test and writes: codes.json, pretest_tables.json, pretest_orphan.png, pretest_browser.html.
Hand codes (by Claude, reading every conflict-cell brief; not blind, no second rater) are embedded below.
Probe answers are parsed automatically from the leading Yes/No."""
import json,re,collections,html
from math import sqrt
rows=[json.loads(l) for l in open('results.jsonl',encoding='utf-8') if l.strip()]
M=['gemma-4-31b-it','deepseek-v4-flash','qwen3.5-397b','glm-5.2']
def yn(t):
    m=re.match(r'\W*(yes|no)\b',t.strip().lower()); return m.group(1) if m else '?'
def wil(k,n,z=1.96):
    if n==0: return (0,0)
    p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;h=z*sqrt(p*(1-p)/n+z*z/(4*n*n))/d; return (max(0,c-h),min(1,c+h))
# ---- hand codes -------------------------------------------------------------------------
def code(r):
    it,cell,m,s=r['item'][0],r['cell'],r['model'],r['sample']
    o=r['source_order']; q='S_ricardian' if it=='A' else 'S_natsel_model'; p='S_rebate01' if it=='A' else 'S_monogamy'
    def cites(x):
        if x not in o: return False
        return bool(re.search(rf'\[[^\]]*\b{o.index(x)+1}\b[^\]]*\]',r['response']))
    c={'cites_p':cites(p),'cites_q':cites(q),'orphan':False,'handles_tension':False}
    if it=='A':
        if cell=='conflict_stripped':
            c['orphan']=not (m=='qwen3.5-397b' and s==2); c['handles_tension']=not c['orphan']
        elif cell in('conflict_kept','conflict_cite_all','easy_pair_alone'):
            c['handles_tension']=c['cites_q']      # every brief that used the Ricardian source scoped or contrasted it
    else:
        if cell=='conflict_stripped':
            c['handles_tension']=(m in('qwen3.5-397b','gemma-4-31b-it')) or (m=='glm-5.2' and s in(0,2,3)) or (m=='deepseek-v4-flash' and s==3)
            c['orphan']=(m=='deepseek-v4-flash' and s==1)
        elif cell=='conflict_kept':
            c['handles_tension']=(m!='deepseek-v4-flash') or s in(0,3)
        else: c['handles_tension']=None
    if cell.startswith('control') or cell.startswith('ablate'): c['handles_tension']=None
    return c
briefs=[r for r in rows if r['kind']=='brief']
for r in briefs:
    r['code']=code(r)
    if r.get('probe_q1'): r['q1']=yn(r['probe_q1']); r['q2']=yn(r['probe_q2'])
json.dump([{k:r[k] for k in('model','item','cell','sample','code')}|{'q1':r.get('q1'),'q2':r.get('q2')} for r in briefs],open('codes.json','w'),indent=0)
# ---- tables -----------------------------------------------------------------------------
T={}
def cellstat(it,cell,key):
    rs=[r for r in briefs if r['item'][0]==it and r['cell']==cell]
    k=sum(bool(key(r)) for r in rs); n=len(rs)
    bym={m:sum(bool(key(r)) for r in rs if r['model']==m) for m in M}
    return {'k':k,'n':n,'ci':wil(k,n),'by_model':bym}
CELLS=['conflict_kept','conflict_stripped','conflict_cite_all','easy_pair_alone','ablate_minus_p','ablate_minus_q','control_kept','control_stripped']
for it in 'AC':
    for c in CELLS:
        T[f'{it}|{c}|orphan']=cellstat(it,c,lambda r:r['code']['orphan'])
        T[f'{it}|{c}|cites_both']=cellstat(it,c,lambda r:r['code']['cites_p'] and r['code']['cites_q'])
        T[f'{it}|{c}|cites_q']=cellstat(it,c,lambda r:r['code']['cites_q'])
        T[f'{it}|{c}|handles']=cellstat(it,c,lambda r:r['code']['handles_tension'])
    for c in ['conflict_kept','conflict_stripped','control_kept','control_stripped']:
        T[f'{it}|{c}|q1_compatible']=cellstat(it,c,lambda r:r['q1']=='yes')
        T[f'{it}|{c}|q2_supports']=cellstat(it,c,lambda r:r['q2']=='yes')
bel=collections.defaultdict(lambda:[0,0])
for r in rows:
    if r['kind']=='belief':
        a=yn(r['response']); endorses=(a=='yes') if r['polarity']=='positive' else (a=='no')
        b=bel[(r['item'][0],r['statement'])]; b[0]+=endorses; b[1]+=1
        bm=bel[(r['item'][0],r['statement'],r['model'])]; bm[0]+=endorses; bm[1]+=1
T['belief']={ '|'.join(k):v for k,v in bel.items()}
json.dump(T,open('pretest_tables.json','w'),indent=1)
def show(k): d=T[k]; return f"{d['k']}/{d['n']} ({d['k']/d['n']:.0%}) by model {[d['by_model'][m] for m in M]}"
for it in 'AC':
    print('ITEM',it)
    for c in CELLS: print(f"  {c:18} orphan {show(f'{it}|{c}|orphan')} | cites both {T[f'{it}|{c}|cites_both']['k']} | handles {T[f'{it}|{c}|handles']['k']}")
    for c in ['conflict_kept','conflict_stripped','control_kept','control_stripped']: print(f"  {c:18} Q1 compatible {show(f'{it}|{c}|q1_compatible')} | Q2 supports {show(f'{it}|{c}|q2_supports')}")
print({k:v for k,v in T['belief'].items() if k.count('|')==1})
# ---- figure -----------------------------------------------------------------------------
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
SURF='#fcfcfb'; INK='#0b0b0b'; INK2='#52514e'; GRID='#e9e8e4'; A='#2a78d6'
fig,(a1,a2)=plt.subplots(1,2,figsize=(11,4.4),facecolor=SURF,gridspec_kw={'width_ratios':[1.25,1]})
labs=[('conflict_kept','Both rivals, hedged text'),('conflict_stripped','Both rivals, one-line text'),('conflict_cite_all','Both rivals, hedged,\n"cite every source"'),('easy_pair_alone','Rival pair alone, hedged'),('ablate_minus_p','Rebate source removed'),('ablate_minus_q','Ricardian source removed')]
def bars(ax,items,title):
    ax.set_facecolor(SURF); ys=list(range(len(items)))[::-1]
    for y,(lab,k,n,extra) in zip(ys,items):
        p=k/n; lo,hi=wil(k,n)
        ax.barh(y,max(p,.004),height=.5,color=A,zorder=2)
        ax.plot([lo,hi],[y,y],color=INK,lw=1.2,zorder=3)
        ax.text(min(hi,1)+.03,y,f"{k} of {n}"+(f"   {extra}" if extra else ''),va='center',fontsize=9.5,color=INK)
    ax.set_yticks(ys); ax.set_yticklabels([i[0] for i in items],fontsize=9.5,color=INK)
    ax.set_xlim(0,1.45); ax.set_xticks([0,.25,.5,.75,1]); ax.set_xticklabels(['0%','25%','50%','75%','100%'],fontsize=9,color=INK2)
    ax.grid(axis='x',color=GRID,lw=1); ax.set_axisbelow(True); ax.tick_params(length=0)
    for s in ax.spines.values(): s.set_visible(False)
    ax.set_title(title,loc='left',fontsize=11,color=INK,fontweight='bold',pad=8)
it1=[]
for c,l in labs:
    d=T[f'A|{c}|orphan']; it1.append((l,d['k'],d['n'],''))
bars(a1,it1,'A. Briefs asserting the unsupported joint conclusion')
b=T['belief']['A|orphan']; s=T['A|conflict_stripped|orphan']; q=T['A|conflict_stripped|q2_supports']
it2=[('Wrote it in the brief\n(one-line text)',s['k'],s['n'],''),('Then said the pair\nsupports it (same chat)',q['k'],q['n'],''),('Called it well supported\n(fresh chat, no sources)',b[0],b[1],'')]
bars(a2,it2,'B. One conclusion, asked three ways')
fig.suptitle('Tax rebates vs Ricardian equivalence: the error appears only with one-line source text',x=.012,ha='left',fontsize=13,color=INK,fontweight='bold')
fig.text(.012,.008,'Four models (gemma-4-31b-it, deepseek-v4-flash, qwen3.5-397b, glm-5.2), 5 samples per cell; same five sources, question and prompt in every "both rivals" cell. Whiskers: 95% Wilson intervals on runs.\nOne hand-built item; briefs coded by reading, not blind. Panel B fresh-chat probes: 3 positive and 3 negative wordings per model.',fontsize=7.5,color=INK2,va='bottom')
fig.tight_layout(rect=[0,.07,1,.94]); fig.savefig('pretest_orphan.png',dpi=200,facecolor=SURF)
# ---- browser ----------------------------------------------------------------------------
NAMES={'S_rebate01':'REBATE (rival p)','S_ricardian':'RICARDIAN (rival q)','S_rebate08':'REBATE 2008 (control partner)','S_multiplier':'distractor','S_highway':'distractor','S_staterules':'distractor','S_monogamy':'MONOGAMY (rival p)','S_natsel_model':'NAT. SELECTION MODEL (rival q)','S_promiscuity_birds':'BIRDS (control partner)','S_antbiomass':'distractor','S_lifespan':'distractor','S_pheromone':'distractor'}
CL={'conflict_kept':'Conflict, hedged text','conflict_stripped':'Conflict, one-line text','conflict_cite_all':'Conflict, hedged, cite-all','easy_pair_alone':'Rival pair alone','ablate_minus_p':'Rival p removed','ablate_minus_q':'Rival q removed','control_kept':'Control, hedged','control_stripped':'Control, one-line'}
e=html.escape; cards=[]
for r in sorted(briefs,key=lambda r:(r['item'],CELLS.index(r['cell']),M.index(r['model']),r['sample'])):
    c=r['code']; chips=[f"<span class=chip>{'Rebates' if r['item'][0]=='A' else 'Eusociality'}</span>",f"<span class=chip>{CL[r['cell']]}</span>",f"<span class=chip>{r['model']}</span>",f"<span class=chip>sample {r['sample']+1}</span>"]
    if c['orphan']: chips.append("<span class='chip bad'>orphan asserted</span>")
    if c['handles_tension']: chips.append("<span class='chip good'>scopes or flags the pair</span>")
    key=', '.join(f"[{i+1}] {NAMES[s]}" for i,s in enumerate(r['source_order']))
    pr=''
    if r.get('probe_q1'): pr=f"<details><summary>Follow-up answers (same conversation): compatible? {r['q1']} · supports conclusion? {r['q2']}</summary><p><b>Q1</b> {e(r['probe_q1'].strip())}</p><p><b>Q2</b> {e(r['probe_q2'].strip())}</p></details>"
    cards.append(f"<div class=card data-i='{r['item'][0]}' data-c='{r['cell']}' data-m='{r['model']}' data-o='{int(c['orphan'])}'><div class=meta>{''.join(chips)}</div><p class=key>{e(key)}</p><p>{e(r['response'].strip())}</p>{pr}<details><summary>Prompt</summary><p>{e(r['prompt'])}</p></details></div>")
opt=lambda d:''.join(f"<option value='{k}'>{v}</option>" for k,v in d.items())
page=f"""<!DOCTYPE html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Pre-test briefs</title><style>
:root{{--bg:#fcfcfb;--card:#fff;--ink:#0b0b0b;--mut:#52514e;--line:#e4e3df;--chip:#f0efec;--warn:#b4500f;--ok:#1b6e3a;--blue:#2a78d6}}
@media(prefers-color-scheme:dark){{:root{{--bg:#1a1a19;--card:#232322;--ink:#f0efec;--mut:#c3c2b7;--line:#383835;--chip:#2e2e2c;--warn:#f0a070;--ok:#6fcf97;--blue:#6da7ec}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,Segoe UI,sans-serif}}header{{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);padding:12px 20px}}
h1{{font-size:17px;margin:0 0 8px}}label{{font-size:13px;color:var(--mut);margin-right:12px}}select{{font:inherit;font-size:13px;background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:3px 6px}}
main{{max-width:900px;margin:0 auto;padding:10px 20px 60px}}.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:14px 0}}
.meta{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px;font-size:12.5px;color:var(--mut)}}.chip{{background:var(--chip);border-radius:20px;padding:1px 9px}}.chip.bad{{color:var(--warn);font-weight:600}}.chip.good{{color:var(--ok);font-weight:600}}
p{{margin:0 0 8px;white-space:pre-wrap;overflow-wrap:anywhere}}.key{{font-size:12.5px;color:var(--mut)}}summary{{cursor:pointer;font-size:13.5px;color:var(--blue)}}details p{{font-size:13.5px;color:var(--mut);margin-top:6px}}#n{{font-size:13px;color:var(--mut)}}
</style></head><body><header><h1>Pre-test: every brief, readable</h1>
<label>Item <select id=i><option value=''>all</option><option value=A>Rebates</option><option value=C>Eusociality</option></select></label>
<label>Condition <select id=c><option value=''>all</option>{opt(CL)}</select></label>
<label>Model <select id=m><option value=''>all</option>{opt({m:m for m in M})}</select></label>
<label>Show <select id=o><option value=''>everything</option><option value=1>orphan asserted</option></select></label> <span id=n></span></header><main>{''.join(cards)}</main>
<script>const S=['i','c','m','o'].map(x=>document.getElementById(x));function f(){{let n=0;document.querySelectorAll('.card').forEach(k=>{{const ok=S.every(s=>!s.value||k.dataset[s.id]===s.value);k.style.display=ok?'':'none';n+=ok}});document.getElementById('n').textContent=n+' briefs'}}S.forEach(s=>s.onchange=f);f()</script></body></html>"""
open('pretest_browser.html','w',encoding='utf-8').write(page); print('wrote figure, browser',len(page))
