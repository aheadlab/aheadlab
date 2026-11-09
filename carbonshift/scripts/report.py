"""Numerical audit and portable figures, without modifying the frozen benchmark."""
import hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results'
def main():
    r=json.loads((OUT/'report.json').read_text());p=json.loads((OUT/'protocol.json').read_text())
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h for name,h in p['hashes'].items())
    decisions=pd.read_csv(OUT/'decisions.csv');selection=json.loads((OUT/'selection.json').read_text())
    assert selection['classic']==r['classic']=='GBM' and selection['ai']==r['ai']=='Timestral-5M'
    assert (decisions.energy_kwh==100).all() and (decisions.duration==4).all()
    assert (decisions.start>=0).all() and (decisions.start+4<=96).all()
    summary=pd.read_csv(OUT/'summary.csv');stats={}
    for phase in ['retro','holdout']:
        part=decisions[decisions.phase.eq(phase)&decisions.zone.isin(r['zones'])]
        means=part.groupby('model').actual_ci.mean()
        a,b=means[r['ai']],means[r['classic']]
        np.testing.assert_allclose(100*(1-a/b),r['results'][phase]['saving_pct'])
        stats[phase]=dict(against_immediate_pct=float(100*(1-a/means['immediate'])),
            against_fixed_pct=float(100*(1-a/means['fixed_hour'])),
            against_sarima_pct=float(100*(1-a/means['SARIMA'])),
            kg_per_mwh_ai=float(a),kg_per_mwh_gbm=float(b),difference_kg_per_mwh=float(b-a),
            cases=int(len(part[part.model.eq(r['ai'])])),all_jobs_completed=True)
    derived=dict(numerical_totals_match=True,frozen_hashes_match=True,selection_unchanged=True,
        energy_and_deadline_invariants=True,stats=stats,
        block14_holdout_note='Not interpretable: with 14 origins a circular block of length 14 contains the whole sample and yields a degenerate interval. Use the reported block-7 interval only; the 176-day sensitivity remains valid.')
    (OUT/'audit.json').write_text(json.dumps(derived,indent=2))
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    order=['Timestral-5M','GBM','hourly_mean','fixed_hour','SARIMA','snaive_week','yesterday','immediate']
    names=['Timestral 5M','GBM','Profilo medio','Orario fisso','SARIMA','Settimana precedente','Giorno precedente','Avvio immediato']
    part=summary[summary.phase.eq('retro')].set_index('model').loc[order]
    fig,ax=plt.subplots(figsize=(10,5),layout='constrained')
    ax.barh(names,part.actual_ci,color=['#367557' if m=='Timestral-5M' else '#bc875f' if m=='GBM' else '#aab5a9' for m in order])
    for i,v in enumerate(part.actual_ci):ax.text(v+.08,i,f'{v:.3f}',va='center',fontsize=9)
    ax.invert_yaxis();ax.set_xlim(0,25);ax.set_xlabel('kg CO₂e attribuiti per MWh di lavoro (meno è meglio)')
    ax.set_title('CarbonShift · stesso lavoro, diversa ora di avvio\n6 zone · 176 giorni · test separato 2025')
    save(fig,'comparison')
    fig,ax=plt.subplots(figsize=(8,3.5),layout='constrained')
    for i,phase in enumerate(['retro','holdout']):
        row=r['results'][phase];lo,hi=row['ci95'];point=row['saving_pct']
        ax.errorbar(point,i,xerr=[[point-lo],[hi-point]],fmt='o',capsize=6,color='#367557' if phase=='retro' else '#bc875f')
    ax.axvline(0,color='#777',ls='--');ax.set_yticks([0,1],['Test 2025 · 176 giorni','Controllo 2026 · 14 giorni'])
    ax.set_xlabel('Riduzione delle emissioni attribuite rispetto a GBM (%)');ax.set_title('Effetto piccolo; il controllo recente non è conclusivo')
    save(fig,'uncertainty')
    print(json.dumps(derived,indent=2))
def save(fig,name):
    fig.savefig(OUT/f'{name}.png',dpi=140);fig.savefig(OUT/f'{name}.svg');plt.close(fig)
    path=OUT/f'{name}.svg';path.write_text('\n'.join(x.rstrip() for x in path.read_text().splitlines())+'\n')
if __name__=='__main__':main()
