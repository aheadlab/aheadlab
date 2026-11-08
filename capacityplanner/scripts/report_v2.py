"""Recheck completed V2 artifacts and render descriptive comparisons."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from capacityplanner.core import MODELS as FORECAST_MODELS,fill_past
from capacityplanner.policy_v2 import margins,reactive_guard,simulate

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('/out') if Path('/out').is_dir() else ROOT/'results/capacity-v2'
MODELS=['last','daily','weekly','weekly_mean','ets','mstl','ridge','5M','28M']


def fmt(value,digits=2):
    return f'{value:,.{digits}f}'.replace(',','_').replace('.',',').replace('_','.')


def secondary_checks(report):
    scores=pd.read_csv(OUT/'forecast_scores.csv');primary=report['primary']
    arrays={name:scores[scores.model.eq(primary[name]['model'])].pivot(index='series',columns='day',values='mae').to_numpy()
        for name in ['ai','classic']}
    rng=np.random.default_rng(20261107);draws=[];count,days=arrays['ai'].shape
    for _ in range(2000):
        ids=rng.integers(count,size=count)
        periods=((rng.integers(days,size=int(np.ceil(days/7)))[:,None]+np.arange(7))%days).ravel()[:days]
        a=np.nanmean(arrays['ai'][ids][:,periods]);b=np.nanmean(arrays['classic'][ids][:,periods])
        draws.append(100*(1-a/b))
    accuracy=dict(label='Secondary descriptive accuracy analysis, primary pair unchanged',
        mae_reduction_pct=float(100*(1-np.nanmean(arrays['ai'])/np.nanmean(arrays['classic']))),
        ci95=np.quantile(draws,[.025,.975]).tolist(),
        institutions_with_lower_mae=int((np.nanmean(arrays['ai'],axis=1)<np.nanmean(arrays['classic'],axis=1)).sum()))
    (OUT/'secondary_accuracy.json').write_text(json.dumps(accuracy,indent=2))
    data=pd.read_parquet(ROOT/'data/processed/v2/selected.parquet')
    first=int(data.index.get_loc(pd.Timestamp('2025-12-08',tz='UTC')))
    results=[];cohort=[];primary_hours={}
    for series in data:
        y=data[series].to_numpy();actual=y[first:].reshape(-1,24);valid=np.isfinite(actual).all(axis=1)
        unit=report['units'][series];guard=reactive_guard(y,first,len(y)-first,1.).reshape(actual.shape)
        initial=max(1,int(np.ceil(fill_past(y[:first+14*24])[-1]/unit)))
        with np.load(ROOT/'data/processed/v2/forecasts'/f'{series}-{report["protocol"]["fingerprint"][:16]}.npz') as archive:pred=archive['median']
        cohort.append(dict(series=series,selection_daily_demand=float(np.nanmean(actual[14:28].sum(axis=1))/unit),
            test_daily_demand=float(np.nanmean(actual[28:].sum(axis=1))/unit)))
        for name in ['ai','classic']:
            chosen=primary[name];model=chosen['model']
            if model not in FORECAST_MODELS:continue
            p=pred[:,FORECAST_MODELS.index(model)]
            for rolling in [False,True]:
                margin=margins(actual,p,chosen['q'],rolling)*chosen['multiplier']
                for reaction in [False,True]:
                    g=guard*chosen['reactive'] if reaction else np.zeros_like(guard)
                    daily,capacity=simulate(p,actual,valid,unit,margin,g,initial)
                    total=np.nansum(daily[:,14:],axis=1)
                    results.append(dict(model=model,series=series,rolling=rolling,reaction=reaction,
                        q=chosen['q'],multiplier=chosen['multiplier'],reactive_factor=chosen['reactive'] if reaction else 0.,
                        unit_hours=float(total[0]),deficit=float(total[1]),demand=float(total[2])))
                    if rolling==(chosen['family']=='adaptive') and reaction==bool(chosen['reactive']):
                        mask=valid[28:];truth=actual[28:][mask]/unit;cap=capacity[28:][mask]
                        covered=actual[28:][mask]<=(p[28:]+margin[28:,None])[mask]
                        primary_hours.setdefault(model,[]).append((np.maximum(truth-cap,0).ravel(),covered.ravel()))
    pd.DataFrame(results).to_csv(OUT/'factorial_ablation_institutions.csv',index=False)
    grouped=pd.DataFrame(results).groupby(['model','rolling','reaction'])[['unit_hours','deficit','demand']].sum()
    grouped['deficit_fraction']=grouped.deficit/grouped.demand
    grouped.to_csv(OUT/'factorial_ablation.csv')
    pd.DataFrame(cohort).to_csv(OUT/'selection_test_load.csv',index=False)
    diagnostic={}
    for model,parts in primary_hours.items():
        deficit=np.concatenate([part[0] for part in parts]);covered=np.concatenate([part[1] for part in parts])
        worst=np.sort(deficit)[::-1];top=max(1,int(np.ceil(.01*len(worst))))
        diagnostic[model]=dict(hours=int(len(deficit)),hours_under=int((deficit>0).sum()),
            fraction_hours_under=float((deficit>0).mean()),margin_coverage=float(covered.mean()),
            largest_hour_normalized_deficit=float(worst[0]),
            top_one_percent_hours_deficit_share=float(worst[:top].sum()/worst.sum()) if worst.sum() else 0.)
    (OUT/'primary_hour_diagnostics.json').write_text(json.dumps(diagnostic,indent=2))
    for name in ['ai','classic']:
        chosen=primary[name]
        if chosen['model'] in FORECAST_MODELS and chosen['family']=='adaptive':
            row=grouped.loc[(chosen['model'],True,bool(chosen['reactive']))]
            np.testing.assert_allclose(row.unit_hours,chosen['unit_hours'])
            np.testing.assert_allclose(row.deficit_fraction,chosen['deficit_fraction'])


def main():
    report=json.loads((OUT/'report.json').read_text());primary=report['primary']
    secondary_checks(report)
    diagnostic=OUT/'diagnosis_hourly.csv'
    if diagnostic.exists():
        old_report=json.loads((ROOT/'results/cesnet/report.json').read_text())
        old_units={s['id']:s['throughput'] for s in old_report['series']}
        hourly=pd.read_csv(diagnostic,dtype={'series':str});hourly=hourly[hourly.phase.eq('test')].copy()
        hourly['raw_deficit']=hourly.deficit*hourly.series.map(old_units)
        hourly['raw_demand']=hourly.demand*hourly.series.map(old_units)
        summary={}
        for model in ['28M','ets','weekly_mean']:
            part=hourly[hourly.model.eq(model)]
            summary[model]=dict(raw_deficit_fraction=float(part.raw_deficit.sum()/part.raw_demand.sum()),
                institution_242_raw_deficit_share=float(part.loc[part.series.eq('242'),'raw_deficit'].sum()/part.raw_deficit.sum()))
        (OUT/'diagnosis_raw_traffic.json').write_text(json.dumps(summary,indent=2))
    table=pd.read_csv(OUT/'summary.csv');institutions=pd.read_csv(OUT/'institution_results.csv')
    grid=pd.read_csv(OUT/'test_grid_descriptive.csv');selection=pd.read_csv(OUT/'selection_policies.csv')
    original=table[table.family.eq('original')].set_index('model').loc[MODELS]
    adaptive=table[table.family.eq('adaptive')].set_index('model').loc[MODELS]
    differences=[]
    for model in MODELS:
        a,o=adaptive.loc[model],original.loc[model]
        differences.append(dict(model=model,original_unit_hours=o.unit_hours,adaptive_unit_hours=a.unit_hours,
            capacity_change_pct=100*(a.unit_hours/o.unit_hours-1),original_deficit=o.deficit_fraction,
            adaptive_deficit=a.deficit_fraction,deficit_change_pp=100*(a.deficit_fraction-o.deficit_fraction),
            original_selection_feasible=bool(o.selection_feasible),adaptive_selection_feasible=bool(a.selection_feasible),
            adaptive_reactive_factor=a.reactive,adaptive_margin_multiplier=a.multiplier,adaptive_quantile=a.q))
    pd.DataFrame(differences).to_csv(OUT/'policy_changes.csv',index=False)
    ablations=[]
    # Select with/without reaction only on the selection period, then look up test.
    for model in MODELS:
        for enabled in [False,True]:
            choices=selection[selection.model.eq(model)&selection.family.eq('adaptive')&selection.reactive.gt(0).eq(enabled)]
            feasible=choices[choices.deficit_fraction.le(.01)]
            chosen=(feasible.sort_values(['unit_hours','deficit_fraction']) if len(feasible)
                    else choices.sort_values(['deficit_fraction','unit_hours'])).iloc[0]
            outcome=grid[grid.key.eq(chosen.key)].iloc[0]
            ablations.append(dict(model=model,reaction=enabled,key=int(chosen.key),
                selection_feasible=bool(chosen.deficit_fraction<=.01),unit_hours=float(outcome.unit_hours),
                deficit_fraction=float(outcome.deficit_fraction)))
    pd.DataFrame(ablations).to_csv(OUT/'reactive_ablation.csv',index=False)
    for row in table.to_dict('records'):
        parts=institutions[institutions.key.eq(row['key'])]
        np.testing.assert_allclose(parts.unit_hours.sum(),row['unit_hours'])
        np.testing.assert_allclose(parts.deficit.sum()/parts.demand.sum(),row['deficit_fraction'])
        np.testing.assert_allclose(parts.raw_deficit.sum()/parts.raw_demand.sum(),row['raw_deficit_fraction'])
    with np.load(OUT/'paired_simulations.npz') as paired:
        for name in ['ai','classic']:
            totals=np.nansum(paired[name],axis=(0,2));row=primary[name]
            np.testing.assert_allclose(totals[0],row['unit_hours'])
            np.testing.assert_allclose(totals[1]/totals[2],row['deficit_fraction'])
    selection_details=json.loads((OUT/'selection_decisions.json').read_text())
    for name in ['ai','classic']:
        assert primary[name]['key']==selection_details['primary_'+name]['key']
    raw_capacity=[]
    for row in table.to_dict('records'):
        parts=institutions[institutions.key.eq(row['key'])]
        capacity=sum(float(r.unit_hours)*report['units'][str(r.series)] for r in parts.itertuples())
        raw_capacity.append(dict(key=row['key'],model=row['model'],family=row['family'],
            capacity_mbps_hours=capacity,raw_deficit_fraction=row['raw_deficit_fraction']))
    pd.DataFrame(raw_capacity).to_csv(OUT/'raw_capacity_descriptive.csv',index=False)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained');x=np.arange(len(MODELS))
    axes[0].bar(x-.18,100*original.deficit_fraction,.36,label='Margine fisso',color='#a8b4c5')
    axes[0].bar(x+.18,100*adaptive.deficit_fraction,.36,label='Politica adattiva selezionata',color='#168292')
    axes[0].axhline(1,ls='--',color='#bd6b30',label='Obiettivo 1%')
    axes[0].set_xticks(x,MODELS,rotation=45);axes[0].set_ylabel('Domanda normalizzata non coperta (%)')
    axes[0].set_title('La protezione riduce il deficit?');axes[0].legend(fontsize=8)
    changes=np.array([r['capacity_change_pct'] for r in differences])
    axes[1].bar(x,changes,color=['#bd6b30' if v>0 else '#168292' for v in changes])
    axes[1].axhline(0,color='#444',linewidth=.7);axes[1].set_xticks(x,MODELS,rotation=45)
    axes[1].set_ylabel('Variazione moduli-ora rispetto al margine fisso (%)')
    axes[1].set_title('Quanta capacità aggiuntiva richiede?')
    fig.suptitle('CESNET 2026 · 24 istituzioni · 56 giorni di test',fontsize=13)
    save(fig,'policy_comparison')
    fig,ax=plt.subplots(figsize=(9,5),layout='constrained')
    primary_keys=[primary['ai']['key'],primary['classic']['key']]
    shown=table[table.family.ne('original')|table.key.isin(primary_keys)]
    for row in shown.itertuples():
        ai=row.model in ['5M','28M'];selected=row.key in [primary['ai']['key'],primary['classic']['key']]
        ax.scatter(row.unit_hours/1000,100*row.deficit_fraction,s=100 if selected else 40,
            marker='*' if ai else 'o',color='#168292' if ai else '#77869c')
        if selected or row.family in ['reactive','fixed']:
            offset=(12,24) if row.key==primary['ai']['key'] else (12,-30) if row.key==primary['classic']['key'] else (5,4)
            ax.annotate(row.model+' / '+row.family,(row.unit_hours/1000,100*row.deficit_fraction),xytext=offset,
                textcoords='offset points',fontsize=9,arrowprops={'arrowstyle':'-','color':'#667085'} if selected else None)
    ax.axhline(1,ls='--',color='#bd6b30',label='Obiettivo deficit 1%')
    ax.set_xlabel('Migliaia di moduli-ora simulati');ax.set_ylabel('Domanda normalizzata non coperta (%)')
    ax.set_title('AI, metodi classici e controlli senza previsioni');ax.legend()
    save(fig,'capacity_frontier')
    text=['# Risultati V2 generati dagli artefatti','',
          'Confronto primario congelato sulla selezione: '+primary['ai']['model']+' / '+primary['ai']['family']+
          ' contro '+primary['classic']['model']+' / '+primary['classic']['family']+'.','',
          '| Misura | AI selezionata | Alternativa classica selezionata |','|---|---:|---:|',
          '| Moduli-ora | '+fmt(primary['ai']['unit_hours'],0)+' | '+fmt(primary['classic']['unit_hours'],0)+' |',
          '| Deficit normalizzato | '+fmt(100*primary['ai']['deficit_fraction'],3)+'% | '+fmt(100*primary['classic']['deficit_fraction'],3)+'% |',
          '| Deficit sul traffico grezzo | '+fmt(100*primary['ai']['raw_deficit_fraction'],3)+'% | '+fmt(100*primary['classic']['raw_deficit_fraction'],3)+'% |','',
          'Riduzione di capacità AI: **'+fmt(primary['saving_pct'])+'%**, intervallo al 95% ['+
          '; '.join(fmt(v) for v in primary['saving_ci'])+']%. Differenza di deficit, intervallo al 95% ['+
          '; '.join(fmt(100*v,3) for v in primary['deficit_delta_ci'])+'] punti percentuali.','',
          '**Criterio primario '+('soddisfatto' if primary['passed'] else 'non soddisfatto')+'.**','',
          '## Tutte le politiche selezionate','',
          '| Modello | Politica | Moduli-ora | Deficit | Istituzioni oltre 5% |','|---|---|---:|---:|---:|']
    for row in table.itertuples():
        text.append('| '+row.model+' | '+row.family+' | '+fmt(row.unit_hours,0)+' | '+fmt(100*row.deficit_fraction,3)+'% | '+str(row.institutions_over_five_percent)+' |')
    text.extend(['','Confronti secondari descrittivi: nessuna sostituzione dei vincitori dopo il test.'])
    (OUT/'RESULTS_GENERATED.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    (OUT/'checks.json').write_text(json.dumps(dict(institution_sums_match=True,paired_arrays_match=True,
        primary_selection_unchanged=True,policies=len(grid),complete_pairs=int(table.pairs.iloc[0])),indent=2))
    print(json.dumps(primary,indent=2),flush=True)


def save(fig,name):
    fig.savefig(OUT/f'{name}.svg');fig.savefig(OUT/f'{name}.png',dpi=140);plt.close(fig)
    path=OUT/f'{name}.svg'
    path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')


if __name__=='__main__':main()
