"""Secondary, descriptive analysis; never changes model or policy selection."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from capacityplanner.benchmark import paired_intervals, SEED


def run(root, out):
    root,out=Path(root),Path(out)
    report=json.loads((out/'report.json').read_text())
    protocol=json.loads((out/'protocol.json').read_text())
    for name,digest in protocol['source_hashes'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest, name
    primary=report['primary']
    with np.load(out/'paired_simulations.npz') as paired:
        ai,baseline=paired['ai'],paired['baseline']
    intervals=paired_intervals(ai,baseline)
    np.testing.assert_allclose(intervals[0],primary['saving_ci'])
    np.testing.assert_allclose(intervals[1],primary['deficit_delta_ci'])
    for arrays,name in [(ai,'ai'),(baseline,'baseline')]:
        total=np.nansum(arrays,axis=(0,2))
        row=next(r for r in report['models'] if r['model']==primary[name])
        np.testing.assert_allclose(total[0],row['unit_hours'])
        np.testing.assert_allclose(total[1]/total[2],row['deficit_fraction'])
    scores=pd.read_csv(out/'scores.csv')
    tests=scores[scores.phase.eq('test')]
    series=sorted(tests.series.unique());days=range(28,56)
    arrays={}
    for label in ['ai','baseline']:
        subset=tests[tests.model.eq(primary[label])]
        arrays[label]=np.stack([subset.pivot(index='series',columns='day',values=metric)
            .reindex(index=series,columns=days).to_numpy() for metric in ['mae','mase']],axis=1)
    np.testing.assert_array_equal(np.isnan(arrays['ai']),np.isnan(arrays['baseline']))
    rng=np.random.default_rng(SEED);gains=[]
    for _ in range(2000):
        ids=rng.integers(len(series),size=len(series))
        times=((rng.integers(28,size=4)[:,None]+np.arange(7))%28).ravel()
        a=np.nanmean(arrays['ai'][ids][:,:,times],axis=(0,2))
        b=np.nanmean(arrays['baseline'][ids][:,:,times],axis=(0,2))
        gains.append(100*(1-a/b))
    means={k:np.nanmean(v,axis=(0,2)) for k,v in arrays.items()}
    gains=np.asarray(gains)
    analysis=dict(label='secondary descriptive forecast analysis; comparison fixed by original selection',
        ai=primary['ai'],baseline=primary['baseline'],
        accuracy={metric:dict(reduction_pct=float(100*(1-means['ai'][i]/means['baseline'][i])),
            ci95=np.quantile(gains[:,i],[.025,.975]).tolist()) for i,metric in enumerate(['mae','mase'])},
        institutions_with_lower_mae=int((np.nanmean(arrays['ai'][:,0],axis=1)<np.nanmean(arrays['baseline'][:,0],axis=1)).sum()),
        complete_test_pairs=int(np.isfinite(arrays['ai'][:,0]).sum()),
        primary_arithmetic_and_intervals_rechecked=True,
        frozen_sources_unchanged=True)
    (out/'secondary_analysis.json').write_text(json.dumps(analysis,indent=2))
    rows=report['models'];labels=[r['model'] for r in rows]
    colors=['#167d8d' if m in ['5M','28M'] else '#8d9aab' for m in labels]
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    axes[0].barh(labels,[r['mase'] for r in rows],color=colors)
    axes[0].set_xlabel('MASE medio (minore è meglio)');axes[0].set_title('Accuratezza sul test finale')
    for r,color in zip(rows,colors):
        axes[1].scatter(r['unit_hours']/1000,100*r['deficit_fraction'],color=color,s=55)
        axes[1].annotate(r['model'],(r['unit_hours']/1000,100*r['deficit_fraction']),xytext=(4,5),textcoords='offset points')
    axes[1].axhline(1,color='#bd6b30',linestyle='--',label='Soglia deficit 1%')
    axes[1].set_ylim(.8,2.6);axes[1].set_xlabel('Migliaia di moduli-ora simulati')
    axes[1].set_ylabel('Domanda normalizzata non coperta (%)')
    axes[1].set_title('Capacità e deficit vanno letti insieme');axes[1].legend(loc='lower right')
    fig.suptitle('Capacity Planner · CESNET · 12 istituzioni, 335 giorni-serie validi',fontsize=13)
    fig.savefig(out/'comparison.svg');fig.savefig(out/'comparison.png',dpi=140);plt.close(fig)
    svg=out/'comparison.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    print(json.dumps(analysis,indent=2),flush=True)
