"""Ladder figure from tables.json. Cumulative share of runs in which the model has surfaced
the pair by each step. Pooled over 3 models and 3 input conditions; item-bootstrap intervals."""
import json, sys, random, collections
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
rows=[json.loads(l) for l in open(sys.argv[1],encoding='utf-8')]
MAIN=['deepseek-v4-flash','qwen3.5-397b','qwen3.8-27b']
KEYS=['flagged','review_flags_pair','conflict_flags_pair','q1_incompatible']
def rung(r):
    for i,k in enumerate(KEYS):
        if r['score'][k]: return i
    return 4
def series(rs):
    by=collections.defaultdict(list)
    for r in rs: by[r['item']].append(rung(r))
    items=sorted(by); rnd=random.Random(1)
    def cum(sample): 
        v=[x for it in sample for x in by[it]]
        return [sum(x<=k for x in v)/len(v) for k in range(4)]
    p=cum(items); bs=sorted(zip(*[cum([rnd.choice(items) for _ in items]) for _ in range(2000)]),key=lambda _:0)
    lo=[sorted(b)[49] for b in bs]; hi=[sorted(b)[1949] for b in bs]
    return p,lo,hi,len(rs),len(items)
SURF='#fcfcfb'; INK='#0b0b0b'; INK2='#52514e'; GRID='#e9e8e4'
COL={'conflict':'#2a78d6','control_regime':'#eb6834','control_same':'#1baf7a'}
LAB={'conflict':'Conflict pair','control_regime':'Regime-scoped control','control_same':'Same-theory control'}
MK={'conflict':'o','control_regime':'s','control_same':'^'}
X=['In the\nparagraph','"Any problems\nwith how it\ncombines sources?"','"Do any sources\nconflict?"','Asked about the\nspecific pair']
fig,axs=plt.subplots(1,2,figsize=(10.5,4.6),sharey=True,facecolor=SURF)
out={}
for ax,(f,title) in zip(axs,[('macro','Macroeconomics'),('cosmo','Cosmology')]):
    ax.set_facecolor(SURF)
    for t in ['conflict','control_regime','control_same']:
        rs=[r for r in rows if r['model'] in MAIN and r['split'].startswith(f) and r['type']==t]
        if not rs: continue
        p,lo,hi,n,ni=series(rs); out[f'{f}|{t}']={'p':p,'lo':lo,'hi':hi,'runs':n,'items':ni}
        ax.fill_between(range(4),lo,hi,color=COL[t],alpha=.13,linewidth=0)
        ax.plot(range(4),p,color=COL[t],lw=2,marker=MK[t],ms=8,mec=SURF,mew=2,solid_capstyle='round',label=f"{LAB[t]} ({ni} items, {n} runs)",zorder=3)
        dy=.045 if t!='control_same' else .045
        ax.annotate(f"{p[3]:.0%}",(3,p[3]),xytext=(8,0),textcoords='offset points',va='center',fontsize=10,color=INK)
        if t=='conflict': ax.annotate(f"{p[0]:.0%}",(0,p[0]),xytext=(0,9),textcoords='offset points',ha='center',fontsize=10,color=INK)
    ax.set_title(title,loc='left',fontsize=12,color=INK,pad=10,fontweight='bold')
    ax.set_xticks(range(4)); ax.set_xticklabels(X,fontsize=8.5,color=INK2)
    ax.set_xlim(-.35,3.5); ax.set_ylim(-.03,1.05)
    ax.set_yticks([0,.25,.5,.75,1]); ax.set_yticklabels(['0%','25%','50%','75%','100%'],fontsize=9,color=INK2)
    ax.grid(axis='y',color=GRID,lw=1); ax.set_axisbelow(True)
    for s in ax.spines.values(): s.set_visible(False)
    ax.tick_params(length=0)
    ax.legend(frameon=False,fontsize=8.5,loc='upper left',labelcolor=INK2,handlelength=2.2)
axs[0].set_ylabel('Runs in which the pair has been\nflagged by this step (cumulative)',fontsize=9.5,color=INK2)
fig.suptitle('How specifically a model must be asked before it flags the conflicting pair',x=.012,ha='left',fontsize=13,color=INK,fontweight='bold')
fig.text(.012,.005,'Three models pooled (deepseek-v4-flash, qwen3.5-397b, qwen3.8-27b), three input conditions pooled. Bands: 95% bootstrap intervals resampling items.\nLabels by a single LLM grader (qwen3.8-27b). The last step uses Q1, which also fires on legitimately combinable regime-scoped pairs.',fontsize=7.5,color=INK2,va='bottom')
fig.tight_layout(rect=[0,.07,1,.94])
fig.savefig('ladder.png',dpi=200,facecolor=SURF); json.dump(out,open('ladder_data.json','w'),indent=1)
for k,v in out.items(): print(k,[f"{x:.0%}" for x in v['p']],[f"{a:.0%}-{b:.0%}" for a,b in zip(v['lo'],v['hi'])],v['runs'],v['items'])
