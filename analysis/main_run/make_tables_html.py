"""Writes tables_for_doc.html: the report's tables as real HTML tables, for copy-paste into Google Docs."""
import json
T=json.load(open('tables.json')); P=T['pooled']; PM=T['per_model']; L=json.load(open('ladder_data.json'))
rg=[json.loads(l) for l in open('regrade.jsonl',encoding='utf-8') if l.strip()]; rg=[r for r in rg if r['type']=='conflict']
def pc(d,ci=True):
    if not d['n']: return '-'
    s=f"{d['p']:.0%}"
    return s+(f" [{d['ci'][0]*100:.0f}-{d['ci'][1]*100:.0f}]" if ci and 0<d['k']<d['n'] else '')
def table(cap,head,rows):
    h=f"<p class=cap>{cap}</p><table><tr>"+''.join(f"<th>{x}</th>" for x in head)+"</tr>"
    for r in rows: h+="<tr>"+''.join(f"<td>{x}</td>" for x in r)+"</tr>"
    return h+"</table>"
out=[]
lab={'macro|conflict':'Macro, conflict pair','macro|control_regime':'Macro, regime-scoped control','macro|control_same':'Macro, same-theory control','cosmo|conflict':'Cosmology, conflict pair','cosmo|control_same':'Cosmology, same-theory control'}
rows=[]
for k in lab:
    d=L[k]; rows.append([f"{lab[k]} ({d['items']} items, {d['runs']} runs)"]+[f"{p:.0%}"+(f" [{lo*100:.0f}-{hi*100:.0f}]" if hi>0 else '') for p,lo,hi in zip(d['p'],d['lo'],d['hi'])])
out.append(table("Table 1. Cumulative share of runs in which the model has flagged the pair by each step. Three models and three input conditions pooled; 95% bootstrap intervals resampling items.",
 ['','In the paragraph','+ generic self-review','+ "do any sources conflict?"','+ asked about the pair'],rows))
nm={'findings':'one-line findings','abstracts':'abstracts','abstracts_anon':'abstracts, names removed'}
rows=[]
for f in ['macro','cosmology']:
    for c in nm:
        d=P[f'{f}|{c}|conflict']; g=d['disclosure_gap']
        rows.append([f.capitalize() if f=='macro' else 'Cosmology',nm[c],d['flag']['n'],pc(d['cited_both'],0),pc(d['flag']),pc(d['orphan']),pc(d['knows_freshQ2']),pc(d['strict_gap'],0),f"{g['v']*100:.0f} pts [{g['ci'][0]*100:.0f}-{g['ci'][1]*100:.0f}]"])
out.append(table('Table 2. Conflict items by field and input. "Knows" = rejects the orphan conclusion in a fresh conversation. Disclosure gap = Knows minus Flagged.',
 ['Field','Input','Runs','Cited both','Flagged in paragraph','Orphan asserted','Knows','Strict gap','Disclosure gap'],rows))
def k(p):
    n=len(p);po=sum(a==b for a,b in p)/n;pa=sum(a for a,_ in p)/n;pb=sum(b for _,b in p)/n;pe=pa*pb+(1-pa)*(1-pb);return po,(po-pe)/(1-pe)
rows=[]
for key,name in (('flagged','Flagged in paragraph'),('orphan_asserted','Orphan asserted')):
    p=[(r['first'][key],r['second'][key]) for r in rg]; po,ka=k(p)
    rows.append([name,f"{po:.0%}",f"{ka:.2f}",sum(a and b for a,b in p),sum(a and not b for a,b in p),sum(b and not a for a,b in p),sum(not a and not b for a,b in p)])
out.append(table(f"Table 3. Agreement between the primary grader (qwen3.8-27b) and a second grader (gemma-4-31b-it) on a stratified sample of {len(rg)} conflict-item paragraphs.",
 ['Label','Agreement',"Cohen's kappa",'Both yes','Primary only','Second only','Both no'],rows))
rows=[]
for m in ['deepseek-v4-flash','qwen3.5-397b','qwen3.8-27b','glm-5.2','claude-opus-5-5 (subagent)']:
    for f in ['macro','cosmology']:
        d=PM.get(f'{m}|{f}|conflict')
        if d: rows.append([m+(' (incomplete)' if m=='glm-5.2' else ''),f,d['n'],pc(d['flag'],0),pc(d['orphan'],0),pc(d['knows'],0),pc(d['strict'],0),f"{d['mean_rung']:.2f}"])
out.append(table("Table 4 (appendix). Conflict items by model, all inputs pooled. Mean step: 0 = flagged in the paragraph, 3 = when asked about the pair, 4 = never.",
 ['Model','Field','Runs','Flagged','Orphan','Knows','Strict gap','Mean step'],rows))
css="body{font:14px/1.45 Arial,sans-serif;max-width:900px;margin:30px auto;padding:0 20px;color:#111}table{border-collapse:collapse;margin:6px 0 28px;width:100%}th,td{border:1px solid #999;padding:5px 8px;text-align:left;font-size:13px;vertical-align:top}th{background:#eee}.cap{font-style:italic;margin:0 0 4px}.how{background:#f4f4f0;border:1px solid #ccc;padding:10px 14px;margin-bottom:26px}"
open('tables_for_doc.html','w',encoding='utf-8').write(f"<!DOCTYPE html><html lang=en><head><meta charset=utf-8><title>Tables for the report</title><style>{css}</style></head><body><div class=how><b>How to use:</b> drag to select one caption and its table, copy (Ctrl+C), click in your Google Doc where it should go, paste (Ctrl+V). It arrives as an editable table.</div>"+''.join(out)+"</body></html>")
print('tables written'); print(rows[0])
