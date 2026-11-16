"""Figure 2: disclosure gap. For conflict items, share of paragraphs that flag the pair unprompted
vs share of runs that reject the orphan conclusion when asked in a fresh conversation. From tables.json."""
import json
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
T=json.load(open('tables.json'))['pooled']
SURF='#fcfcfb'; INK='#0b0b0b'; INK2='#52514e'; GRID='#e9e8e4'; A='#2a78d6'; B='#eb6834'
rows=[('macro','findings','Macro · one-line findings'),('macro','abstracts','Macro · abstracts'),('macro','abstracts_anon','Macro · abstracts, names removed'),
      ('cosmology','findings','Cosmology · one-line findings'),('cosmology','abstracts','Cosmology · abstracts'),('cosmology','abstracts_anon','Cosmology · abstracts, names removed')]
fig,ax=plt.subplots(figsize=(9.2,4.0),facecolor=SURF); ax.set_facecolor(SURF)
ys=list(range(len(rows)))[::-1]
for y,(f,c,lab) in zip(ys,rows):
    d=T[f'{f}|{c}|conflict']; fl=d['flag']; kn=d['knows_freshQ2']
    ax.plot([fl['p'],kn['p']],[y,y],color=GRID,lw=6,solid_capstyle='round',zorder=1)
    for v,col,mk in ((fl,A,'o'),(kn,B,'s')):
        ax.plot(v['ci'],[y,y],color=col,lw=2,alpha=.55,zorder=2)
        ax.plot(v['p'],y,mk,color=col,ms=10,mec=SURF,mew=2,zorder=3)
    ax.annotate(f"{fl['p']:.0%}",(fl['p'],y),xytext=(0,11),textcoords='offset points',ha='center',fontsize=9.5,color=INK)
    ax.annotate(f"{kn['p']:.0%}",(kn['p'],y),xytext=(0,11),textcoords='offset points',ha='center',fontsize=9.5,color=INK)
ax.set_yticks(ys); ax.set_yticklabels([r[2]+f"  (n={T[r[0]+'|'+r[1]+'|conflict']['flag']['n']})" for r in rows],fontsize=9.5,color=INK)
ax.set_xlim(-.03,1.06); ax.set_ylim(-.6,len(rows)-.3)
ax.set_xticks([0,.25,.5,.75,1]); ax.set_xticklabels(['0%','25%','50%','75%','100%'],fontsize=9,color=INK2)
ax.grid(axis='x',color=GRID,lw=1); ax.set_axisbelow(True); ax.tick_params(length=0)
for s in ax.spines.values(): s.set_visible(False)
ax.plot([],[],'o',color=A,ms=9,mec=SURF,mew=2,label='Paragraph flags the pair unprompted')
ax.plot([],[],'s',color=B,ms=9,mec=SURF,mew=2,label='Rejects the joint conclusion when asked (fresh conversation)')
ax.legend(frameon=False,fontsize=9,loc='lower left',bbox_to_anchor=(-.62,1.0),ncol=2,labelcolor=INK2,columnspacing=1.5,handletextpad=.3)
ax.set_xlabel('Share of runs on conflict items',fontsize=9.5,color=INK2)
fig.suptitle('What models say unprompted vs what they say when asked',x=.012,ha='left',fontsize=13,color=INK,fontweight='bold')
fig.text(.012,.005,'Three models pooled. Lines: 95% bootstrap intervals resampling items. On same-theory controls both rates are 0% (0 of 90 runs).',fontsize=7.5,color=INK2,va='bottom')
fig.tight_layout(rect=[0,.04,1,.95]); fig.savefig('disclosure_gap.png',dpi=200,facecolor=SURF); print('ok')
