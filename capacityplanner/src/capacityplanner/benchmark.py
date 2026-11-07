"""Selection precedes test; matched capacity policies and paired uncertainty."""
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import pandas as pd
from .core import MODELS, REVISIONS, CONTEXT, predict, fill_past, plan

LEVELS = [0.,.5,.75,.9,.95,.975,.99,1.]
SEED = 20261106


def simulate_policy(predictions, actual, valid, unit, adjustment, initial):
    """Continuous decision state across days; missing targets never become zeros."""
    costs, deficits, demand = [],[],[]
    last = initial
    for day in range(len(predictions)):
        units = plan(predictions[day],unit,adjustment,last,1)
        last = int(units[-1])
        if valid[day]:
            costs.append(float(units.sum()))
            deficits.append(float(np.maximum(actual[day]/unit-units,0).sum()))
            demand.append(float((actual[day]/unit).sum()))
        else:
            costs.append(np.nan); deficits.append(np.nan); demand.append(np.nan)
    return np.array([costs,deficits,demand])


def choose(candidates):
    feasible=[r for r in candidates if r['deficit_fraction']<=.01]
    pool=feasible or candidates
    return min(pool,key=lambda r:(r['unit_hours'],r['deficit_fraction']) if feasible
               else (r['deficit_fraction'],r['unit_hours']))


def paired_intervals(ai,baseline,repetitions=2000):
    """(series, metric[cost,deficit,demand],day), paired crossed block bootstrap."""
    if ai.shape!=baseline.shape or ai.ndim!=3 or ai.shape[1]!=3:
        raise ValueError('Paired simulation shapes differ')
    if not np.array_equal(np.isnan(ai),np.isnan(baseline)):
        raise ValueError('Paired missing observations differ')
    rng=np.random.default_rng(SEED); series,_,days=ai.shape
    savings,delta=[],[]
    for _ in range(repetitions):
        ids=rng.integers(series,size=series)
        starts=rng.integers(days,size=int(np.ceil(days/7)))
        indices=((starts[:,None]+np.arange(7))%days).ravel()[:days]
        a=np.nansum(ai[ids][:,:,indices],axis=(0,2)); b=np.nansum(baseline[ids][:,:,indices],axis=(0,2))
        savings.append(100*(1-a[0]/b[0]));delta.append(a[1]/a[2]-b[1]/b[2])
    return np.quantile(savings,[.025,.975]).tolist(),np.quantile(delta,[.025,.975]).tolist()


def run(root,out):
    root,out=Path(root),Path(out);out.mkdir(parents=True,exist_ok=True)
    data=pd.read_parquet(root/'data/processed/selected.parquet')
    meta=json.loads((root/'data/processed/selection.json').read_text())
    first=len(data)-56*24
    if first<CONTEXT:raise ValueError('Insufficient common history')
    hashes={str(path.relative_to(root)):hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [root/'src/capacityplanner/core.py',root/'src/capacityplanner/benchmark.py',root/'docs/PROTOCOL.md']}
    fingerprint=hashlib.sha256(json.dumps(dict(hashes=hashes,data=meta),sort_keys=True).encode()).hexdigest()
    (out/'protocol.json').write_text(json.dumps(dict(seed=SEED,models=list(MODELS),revisions=REVISIONS,
        context=CONTEXT,calibration_days=14,selection_days=14,test_days=28,horizon=24,
        capacity_levels=LEVELS,deficit_target=.01,noninferiority=.002,minimum_saving_pct=10,
        source_hashes=hashes,selection=meta,created_utc=str(pd.Timestamp.now(tz='UTC'))),indent=2))
    begun=time.time(); scores=[]; predictions={}; actuals={}; masks={}; units={}; replays={}
    cache=root/'data/processed/cache';cache.mkdir(exist_ok=True)
    for index,series in enumerate(data):
        y=data[series].to_numpy(dtype=float)
        unit=max(float(np.nanquantile(y[:first],.95))/10,1e-9); units[series]=unit
        actual=y[first:].reshape(56,24); valid=np.isfinite(actual).all(axis=1)
        if valid[:14].sum()<7 or valid[14:28].sum()<7 or valid[28:].sum()<14:
            raise ValueError(f'Insufficient complete blocks for preselected series {series}')
        file=cache/f'{series}-{fingerprint[:16]}.npz'
        if file.exists():
            with np.load(file) as saved: all_pred=saved['predictions']
            assert all_pred.shape==(56,len(MODELS),3,24)
        else:
            all_pred=np.full((56,len(MODELS),3,24),np.nan)
            for day in range(56):
                cutoff=first+day*24
                for m,model in enumerate(MODELS):
                    result=predict(y[:cutoff],model)
                    all_pred[day,m,0]=result['median']
                    if 'p10' in result:
                        all_pred[day,m,1]=result['p10'];all_pred[day,m,2]=result['p90']
                if day%7==6:print(f'{series} day {day+1}/56 ({index+1}/{len(data.columns)} series) {time.time()-begun:.0f}s',flush=True)
            np.savez_compressed(file,predictions=all_pred)
        predictions[series]=all_pred;actuals[series]=actual;masks[series]=valid
        for m,model in enumerate(MODELS):
            residuals=(actual[:14]-all_pred[:14,m,0])[np.isfinite(actual[:14])]
            lo,hi=np.quantile(residuals,[.1,.9])
            for day in range(56):
                if not valid[day]:continue
                cutoff=first+day*24
                h=fill_past(y[max(0,cutoff-CONTEXT):cutoff])
                scale=float(np.mean(np.abs(h[168:]-h[:-168])))
                p=all_pred[day,m,0];truth=actual[day]
                lower=np.maximum(0,p+lo);upper=np.maximum(0,p+hi)
                low_err=truth-lower;high_err=truth-upper
                row=dict(series=series,model=model,day=day,origin=str(data.index[cutoff]),
                    phase='calibration' if day<14 else 'selection' if day<28 else 'test',
                    mae=float(np.abs(truth-p).mean()),mase=float(np.abs(truth-p).mean()/scale) if scale>0 else np.nan,
                    bias=float((p-truth).mean()),coverage80=float(((truth>=lower)&(truth<=upper)).mean()),
                    interval_width=float((upper-lower).mean()),
                    pinball=float((np.maximum(.1*low_err,-.9*low_err).mean()+np.maximum(.9*high_err,-.1*high_err).mean())/2))
                if model in REVISIONS:
                    row['raw_coverage80']=float(((truth>=all_pred[day,m,1])&(truth<=all_pred[day,m,2])).mean())
                scores.append(row)
        replay_day=int(np.flatnonzero(valid)[-1]);cutoff=first+replay_day*24
        replay_forecasts={}
        for m,model in enumerate(MODELS):
            f={'median':all_pred[replay_day,m,0].tolist()}
            if model in REVISIONS:f.update(p10=all_pred[replay_day,m,1].tolist(),p90=all_pred[replay_day,m,2].tolist())
            replay_forecasts[model]=f
        history=fill_past(y[max(0,cutoff-168):cutoff])
        replays[series]=dict(times=[str(t) for t in data.index[cutoff:cutoff+24]],actual=actual[replay_day].tolist(),
            history=[dict(time=str(t),value=float(v)) for t,v in zip(data.index[cutoff-168:cutoff],history)],forecasts=replay_forecasts)
    pd.DataFrame(scores).to_csv(out/'scores.csv',index=False)
    # No test objective is used in this selection block.
    policies=[]; simulations={}; margins={}
    for m,model in enumerate(MODELS):
        for level in LEVELS:
            key=(model,level);simulations[key]=[];margins[key]={}
            for series in data:
                p=predictions[series][:,m,0];actual=actuals[series]
                residuals=(actual[:14]-p[:14])[np.isfinite(actual[:14])]
                margin=max(0.,float(np.quantile(residuals,level)));margins[key][series]=margin
                initial=max(1,int(np.ceil(fill_past(data[series].to_numpy()[:first+14*24])[-1]/units[series])))
                simulations[key].append(simulate_policy(p[14:],actual[14:],masks[series][14:],units[series],margin,initial))
            simulations[key]=np.array(simulations[key])
            totals=np.nansum(simulations[key][:,:,:14],axis=(0,2))
            policies.append(dict(model=model,level=level,unit_hours=float(totals[0]),deficit_fraction=float(totals[1]/totals[2])))
    chosen={model:choose([p for p in policies if p['model']==model]) for model in MODELS}
    ai=choose([chosen[m] for m in REVISIONS]); baseline=choose([chosen[m] for m in MODELS if m not in REVISIONS])
    (out/'selection_decisions.json').write_text(json.dumps(dict(models=chosen,primary_ai=ai,primary_baseline=baseline),indent=2))
    pd.DataFrame(policies).to_csv(out/'selection_policies.csv',index=False)
    # Test reporting starts only after choices are fixed.
    table=[];test_sim={}; all_policy_rows=[]
    score_frame=pd.DataFrame(scores);tests=score_frame[score_frame.phase.eq('test')]
    for key,simulation in simulations.items():
        totals=np.nansum(simulation[:,:,14:],axis=(0,2))
        all_policy_rows.append(dict(model=key[0],level=key[1],unit_hours=float(totals[0]),deficit_fraction=float(totals[1]/totals[2])))
    for model in MODELS:
        choice=chosen[model];simulation=simulations[(model,choice['level'])][:,:,14:];test_sim[model]=simulation
        totals=np.nansum(simulation,axis=(0,2)); metric=tests[tests.model.eq(model)]
        table.append(dict(model=model,level=choice['level'],unit_hours=float(totals[0]),
            deficit_fraction=float(totals[1]/totals[2]),selection_feasible=choice['deficit_fraction']<=.01,
            mae=float(metric.mae.mean()),mase=float(metric.mase.mean()),bias=float(metric.bias.mean()),
            coverage80=float(metric.coverage80.mean()),pinball=float(metric.pinball.mean()),
            test_pairs=len(metric)))
    lookup={r['model']:r for r in table};a,b=lookup[ai['model']],lookup[baseline['model']]
    ci,di=paired_intervals(test_sim[ai['model']],test_sim[baseline['model']])
    saving=100*(1-a['unit_hours']/b['unit_hours'])
    passed=bool(ai['deficit_fraction']<=.01 and baseline['deficit_fraction']<=.01
        and a['deficit_fraction']<=.01 and b['deficit_fraction']<=.01 and saving>=10 and ci[0]>0 and di[1]<=.002)
    primary=dict(ai=ai['model'],baseline=baseline['model'],saving_pct=saving,saving_ci=ci,
                 deficit_delta_ci=di,passed=passed,ai_deficit=a['deficit_fraction'],baseline_deficit=b['deficit_fraction'])
    report=dict(status='complete',headline='Il piano AI soddisfa il criterio operativo sul campione.' if passed
        else 'Il confronto distingue precisione e capacità: il criterio operativo non è soddisfatto.',
        series=[dict(id=s,label=f'Istituzione {s}',throughput=units[s]) for s in data],
        models=table,primary=primary,replays=replays,
        source=dict(name='CESNET-TimeSeries24',url='https://doi.org/10.1038/s41597-025-04603-x',license='CC-BY-4.0'),
        protocol=dict(training_hours=first,calibration_days=14,selection_days=14,test_days=28,
            context=CONTEXT,units='hourly mean Mbit/s; simulated capacity modules',
            incomplete_test_pairs=int(sum((~masks[s][28:]).sum() for s in data)),
            bootstrap='2000 paired crossed institution + circular seven-day block resamples',
            elapsed_seconds=time.time()-begun,fingerprint=fingerprint))
    (out/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    pd.DataFrame(table).to_csv(out/'summary.csv',index=False)
    pd.DataFrame(all_policy_rows).to_csv(out/'test_policy_grid_descriptive.csv',index=False)
    # Arrays for independent rechecking of the selected paired comparison.
    np.savez_compressed(out/'paired_simulations.npz',ai=test_sim[ai['model']],baseline=test_sim[baseline['model']])
    print(json.dumps(primary,indent=2),flush=True)
