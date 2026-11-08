"""Follow-up research; preserve the first experiment and use new observations."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from capacityplanner.core import MODELS, REVISIONS, CONTEXT, fill_past, plan, predict
from capacityplanner.policy_v2 import reactive_guard,margins,simulate,candidates,select,bootstrap
import time

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('/out') if Path('/out').is_dir() else ROOT/'results/capacity-v2'
SEED=20261107
START=pd.Timestamp('2025-09-15',tz='UTC')
CAL=pd.Timestamp('2025-12-08',tz='UTC')
TEST=pd.Timestamp('2026-01-05',tz='UTC')
STOP=pd.Timestamp('2026-03-02',tz='UTC')
PROCESSED=ROOT/'data/processed/v2'


def dump(name,value):
    (OUT/name).write_text(json.dumps(value,indent=2,allow_nan=False))


def inspect():
    import tables
    with tables.open_file(ROOT/'data/raw/institutions26-hour.h5') as file:
        print(file)
        for node in file.walk_nodes():
            if hasattr(node,'colnames'):
                print(node._v_pathname,node.shape,node.colnames,flush=True)
                if 'agg_' not in node._v_pathname or 'id_ranges' in node._v_pathname:
                    print(node[:20] if len(node)<100 else node[:2],flush=True)
                    if 'times_' in node._v_pathname:print('LAST',node[-2:],flush=True)


def source_hashes():
    names=['docs/PROTOCOL_V2.md','src/capacityplanner/core.py',
           'src/capacityplanner/policy_v2.py','scripts/research_v2.py']
    return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names}


def prepare():
    import tables
    source=json.loads((ROOT/'data/source26.json').read_text())
    raw=ROOT/'data/raw/institutions26-hour.h5';digest=hashlib.sha256()
    with raw.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    if digest.hexdigest()!=source['sha256']:raise ValueError('Source digest mismatch')
    hours=pd.date_range(START,STOP,freq='h',inclusive='left')
    series={};exclusions=[]
    with tables.open_file(raw) as file:
        timestamps=pd.DataFrame.from_records(file.root.times.times_1_hour[:])
        timestamps['timestamp']=pd.to_datetime(timestamps['time'],unit='s',utc=True)
        mapping=timestamps.set_index('id_time')['timestamp']
        if mapping.index.has_duplicates or mapping.duplicated().any():raise ValueError('Duplicate time grid')
        for outage in file.root.outages[:]:
            if outage['part']!=b'main':continue
            start=pd.Timestamp(int(outage['last_data_before']),unit='s',tz='UTC').floor('h')
            stop=pd.Timestamp(int(outage['data_resumed']),unit='s',tz='UTC').ceil('h')
            if start<STOP and stop>START:
                exclusions.append(dict(reason='monitoring outage including boundary hours',start=str(start),stop=str(stop)))
        for change in file.root.europe_time_changes[:]:
            if change['measured_from']!=b'main':continue
            date=pd.Timestamp(int(change['date']),unit='s',tz='UTC').tz_convert('Europe/Prague').normalize()
            start=date.tz_convert('UTC');stop=(date+pd.DateOffset(days=1)).tz_convert('UTC')
            if start<STOP and stop>START:
                exclusions.append(dict(reason='DST local calendar day, conservative exclusion',start=str(start),stop=str(stop)))
        mask=np.zeros(len(hours),dtype=bool)
        for exclusion in exclusions:mask|=(hours>=pd.Timestamp(exclusion['start']))&(hours<pd.Timestamp(exclusion['stop']))
        table=file.root.institutions.agg_1_hour
        for item in file.root.institutions.id_ranges_agg_1_hour[:]:
            identifier=int(item['id_institution'])
            records=table.read(int(item['start']),int(item['end']))
            if not np.all(records['id_institution']==identifier):raise ValueError('Invalid row ranges')
            time_index=pd.DatetimeIndex(mapping.reindex(records['id_time']).array)
            if time_index.hasnans or time_index.has_duplicates:raise ValueError('Invalid institution timestamps')
            values=records['n_bytes'].astype(float)*8/3600/1e6
            if not np.isfinite(values).all() or (values<0).any():raise ValueError('Invalid measured values')
            s=pd.Series(values,index=time_index).reindex(hours)
            s.iloc[mask]=np.nan;series[str(identifier)]=s
    frame=pd.DataFrame(series);training=frame.loc[frame.index<CAL]
    eligible=sorted([s for s in frame if training[s].notna().mean()>=.95 and training[s].gt(0).mean()>=.5],key=int)
    selected=sorted(np.random.default_rng(SEED).choice(eligible,size=24,replace=False).tolist(),key=int)
    selected_frame=frame[selected];first=int(selected_frame.index.get_loc(CAL));counts={}
    for s in selected:
        valid=np.isfinite(selected_frame[s].to_numpy()[first:].reshape(-1,24)).all(axis=1)
        counts[s]=dict(calibration=int(valid[:14].sum()),selection=int(valid[14:28].sum()),test=int(valid[28:].sum()))
        if min(counts[s]['calibration'],counts[s]['selection'])<7 or counts[s]['test']<28:
            raise ValueError(f'Preselected institution {s} has insufficient complete days: {counts[s]}')
    PROCESSED.mkdir(parents=True,exist_ok=True)
    selected_frame.to_parquet(PROCESSED/'selected.parquet')
    metadata=dict(source=source,seed=SEED,selected_ids=selected,eligible_count=len(eligible),
        start=str(START),calibration_start=str(CAL),selection_start=str(CAL+pd.Timedelta(days=14)),
        test_start=str(TEST),end_exclusive=str(STOP),hours=len(hours),training_hours=first,
        exclusion_intervals=exclusions,excluded_common_hours=int(mask.sum()),complete_days=counts,
        training_coverage={s:float(training[s].notna().mean()) for s in selected},
        values_sha256=hashlib.sha256(selected_frame.to_numpy().tobytes()).hexdigest())
    (PROCESSED/'selection.json').write_text(json.dumps(metadata,indent=2))
    dump('data_selection.json',metadata)
    print(json.dumps(metadata,indent=2),flush=True)


def forecast():
    data=pd.read_parquet(PROCESSED/'selected.parquet')
    selection=json.loads((PROCESSED/'selection.json').read_text())
    hashes=source_hashes()
    fingerprint=hashlib.sha256(json.dumps(dict(hashes=hashes,selection=selection),sort_keys=True).encode()).hexdigest()
    manifest=dict(created_utc=str(pd.Timestamp.now(tz='UTC')),hashes=hashes,fingerprint=fingerprint,
        selection=selection,models=list(MODELS),revisions=REVISIONS,seed=SEED,
        calibration_start=str(CAL),test_start=str(TEST),end_exclusive=str(STOP))
    dump('protocol.json',manifest)
    cache=PROCESSED/'forecasts';cache.mkdir(exist_ok=True)
    first=int(data.index.get_loc(CAL));days=(len(data)-first)//24;begun=time.time()
    for i,series in enumerate(data):
        path=cache/f'{series}-{fingerprint[:16]}.npz'
        if path.exists():
            with np.load(path) as saved:assert saved['median'].shape==(days,len(MODELS),24)
            continue
        y=data[series].to_numpy();predictions=np.empty((days,len(MODELS),24))
        for day in range(days):
            cutoff=first+day*24
            for m,model in enumerate(MODELS):predictions[day,m]=predict(y[:cutoff],model)['median']
            if day%14==13:print(f'{series}: {day+1}/{days} days ({i+1}/{len(data.columns)} institutions) {time.time()-begun:.0f}s',flush=True)
        np.savez_compressed(path,median=predictions)
    dump('forecast_run.json',dict(elapsed_seconds=time.time()-begun,series=len(data.columns),
        days=days,forecasts=len(data.columns)*days*len(MODELS),fingerprint=fingerprint))


def evaluate():
    manifest=json.loads((OUT/'protocol.json').read_text())
    if source_hashes()!=manifest['hashes']:raise ValueError('Frozen source changed after forecasts')
    data=pd.read_parquet(PROCESSED/'selected.parquet');first=int(data.index.get_loc(CAL))
    configs=[dict(model=model,**c) for model in MODELS for c in candidates()]
    configs += [dict(model='reactive_only',family='reactive',q=0.,multiplier=f,reactive=f) for f in [1.,1.25,1.5,2.]]
    configs += [dict(model='fixed_p99',family='fixed',q=0.,multiplier=f,reactive=0.) for f in [1.,1.5,2.]]
    simulations={i:[] for i in range(len(configs))};details={i:[] for i in range(len(configs))}
    forecast_scores=[];units={};diagnostic_hours=[]
    for series in data:
        y=data[series].to_numpy();actual=y[first:].reshape(-1,24);valid=np.isfinite(actual).all(axis=1)
        unit=max(float(np.nanquantile(y[:first],.95))/10,1e-9);units[series]=unit
        with np.load(PROCESSED/'forecasts'/f'{series}-{manifest["fingerprint"][:16]}.npz') as archive:
            predictions=archive['median']
        guard=reactive_guard(y,first,len(y)-first,1.).reshape(actual.shape)
        initial=max(1,int(np.ceil(fill_past(y[:first+14*24])[-1]/unit)))
        calibrated={(model,rolling,q):margins(actual,predictions[:,m],q,rolling)
            for m,model in enumerate(MODELS) for rolling,qs in [(False,[0.,.5,.75,.9,.95,.975,.99,1.]),(True,[.95,.99,1.])]
            for q in qs}
        for m,model in enumerate(MODELS):
            for day in range(28,len(actual)):
                if not valid[day]:continue
                cutoff=first+day*24;h=fill_past(y[cutoff-CONTEXT:cutoff]);scale=np.abs(h[168:]-h[:-168]).mean()
                error=np.abs(actual[day]-predictions[day,m]).mean()
                forecast_scores.append(dict(series=series,model=model,day=day,mae=float(error),
                    mase=float(error/scale) if scale>0 else np.nan))
        for key,config in enumerate(configs):
            model=config['model'];family=config['family']
            if model in MODELS:
                p=predictions[:,MODELS.index(model)]
                margin=calibrated[(model,family=='adaptive',config['q'])]*config['multiplier']
                g=guard*config['reactive']
            elif family=='reactive':
                p=np.zeros_like(actual);margin=np.zeros(len(actual));g=guard*config['multiplier']
            else:
                p=np.full_like(actual,np.nanquantile(y[:first],.99)*config['multiplier'])
                margin=np.zeros(len(actual));g=np.zeros_like(actual)
            daily,capacity=simulate(p,actual,valid,unit,margin,g,initial)
            simulations[key].append(daily)
            selected=valid[28:];truth=actual[28:][selected]/unit;cap=capacity[28:][selected]
            deficit=np.maximum(truth-cap,0);total=float(truth.sum())
            sorted_deficit=np.sort(deficit.ravel())[::-1]
            details[key].append(dict(series=series,unit_hours=int(cap.sum()),deficit=float(deficit.sum()),
                demand=total,deficit_fraction=float(deficit.sum()/total) if total else 0.,
                raw_deficit=float(deficit.sum()*unit),raw_demand=total*unit,
                hours_under=int((deficit>0).sum()),largest_hour_deficit=float(deficit.max()),
                hours=len(deficit.ravel()),valid_days=int(selected.sum()),
                margin_coverage=float(np.mean(actual[28:][selected]<=(p[28:]+margin[28:,None])[selected]))
                    if model in MODELS else None))
            # Only retain detailed rows for the choices after selection below.
        print('Simulated',series,flush=True)
    simulations={k:np.asarray(v) for k,v in simulations.items()}
    selection=[]
    for key,config in enumerate(configs):
        total=np.nansum(simulations[key][:,:,:14],axis=(0,2))
        selection.append(dict(key=key,**config,unit_hours=float(total[0]),deficit_fraction=float(total[1]/total[2])))
    groups={}
    for row in selection:groups.setdefault((row['model'],row['family']),[]).append(row)
    choices=[select(rows) for rows in groups.values()]
    ai=select([r for r in selection if r['model'] in REVISIONS])
    classic=select([r for r in selection if r['model'] not in REVISIONS])
    # This artifact is persisted before any test metric is selected or compared.
    dump('selection_decisions.json',dict(primary_ai=ai,primary_classic=classic,model_families=choices))
    pd.DataFrame(selection).to_csv(OUT/'selection_policies.csv',index=False)
    table=[];allrows=[]
    for chosen in choices:
        key=chosen['key'];rows=details[key];allrows.extend([dict(key=key,model=chosen['model'],family=chosen['family'],**r) for r in rows])
        total=np.nansum(simulations[key][:,:,14:],axis=(0,2))
        values=[r['deficit_fraction'] for r in rows]
        table.append(dict(key=key,model=chosen['model'],family=chosen['family'],q=chosen['q'],
            multiplier=chosen['multiplier'],reactive=chosen['reactive'],selection_feasible=chosen['deficit_fraction']<=.01,
            unit_hours=float(total[0]),deficit_fraction=float(total[1]/total[2]),
            raw_deficit_fraction=sum(r['raw_deficit'] for r in rows)/sum(r['raw_demand'] for r in rows),
            institutions_over_one_percent=sum(v>.01 for v in values),institutions_over_five_percent=sum(v>.05 for v in values),
            worst_institution_deficit=max(values),pairs=sum(r['valid_days'] for r in rows)))
    lookup={r['key']:r for r in table}
    a,b=lookup[ai['key']],lookup[classic['key']]
    intervals=bootstrap(simulations[ai['key']][:,:,14:],simulations[classic['key']][:,:,14:])
    saving=100*(1-a['unit_hours']/b['unit_hours'])
    passed=bool(ai['deficit_fraction']<=.01 and classic['deficit_fraction']<=.01 and a['deficit_fraction']<=.01
        and b['deficit_fraction']<=.01 and saving>=10 and intervals['saving_ci'][0]>0 and intervals['deficit_delta_ci'][1]<=.002)
    primary=dict(ai=a,classic=b,saving_pct=saving,**intervals,passed=passed)
    pd.DataFrame(table).to_csv(OUT/'summary.csv',index=False)
    pd.DataFrame(allrows).to_csv(OUT/'institution_results.csv',index=False)
    pd.DataFrame(forecast_scores).to_csv(OUT/'forecast_scores.csv',index=False)
    pd.DataFrame(forecast_scores).groupby('model')[['mae','mase']].mean().to_csv(OUT/'forecast_summary.csv')
    # Full policy grid is descriptive only; never used to change the primary pair.
    grid=[]
    for key,config in enumerate(configs):
        total=np.nansum(simulations[key][:,:,14:],axis=(0,2))
        grid.append(dict(key=key,**config,unit_hours=float(total[0]),deficit_fraction=float(total[1]/total[2])))
    pd.DataFrame(grid).to_csv(OUT/'test_grid_descriptive.csv',index=False)
    np.savez_compressed(OUT/'paired_simulations.npz',ai=simulations[ai['key']][:,:,14:],classic=simulations[classic['key']][:,:,14:])
    dump('report.json',dict(status='complete',primary=primary,models=table,protocol=manifest,
        total_policies=len(configs),units=units,forecast_metrics=pd.DataFrame(forecast_scores).groupby('model')[['mae','mase']].mean().to_dict('index')))
    print(json.dumps(primary,indent=2),flush=True)


def diagnose():
    original=ROOT/'results/cesnet'
    report=json.loads((original/'report.json').read_text())
    choices=json.loads((original/'selection_decisions.json').read_text())['models']
    data=pd.read_parquet(ROOT/'data/processed/selected.parquet')
    first=len(data)-56*24;rows=[]
    for series in data:
        y=data[series].to_numpy();unit=max(float(np.nanquantile(y[:first],.95))/10,1e-9)
        file=ROOT/'data/processed/cache'/f'{series}-{report["protocol"]["fingerprint"][:16]}.npz'
        with np.load(file) as archive: predictions=archive['predictions'][:,:,0,:]
        actual=y[first:].reshape(56,24)
        for m,model in enumerate(MODELS):
            residual=(actual[:14]-predictions[:14,m])[np.isfinite(actual[:14])]
            margin=max(0.,float(np.quantile(residual,choices[model]['level'])))
            previous=max(1,int(np.ceil(fill_past(y[:first+14*24])[-1]/unit)))
            for day in range(14,56):
                capacity=plan(predictions[day,m],unit,margin,previous,1)
                previous=int(capacity[-1])
                if not np.isfinite(actual[day]).all():continue
                for hour in range(24):
                    truth=actual[day,hour]/unit
                    no_delay=max(1,np.ceil((predictions[day,m,hour]+margin)/unit))
                    rows.append(dict(series=series,model=model,day=day,hour=hour,
                        time=str(data.index[first+day*24+hour]),
                        phase='selection' if day<28 else 'test',
                        demand=truth,units=int(capacity[hour]),deficit=max(0,truth-capacity[hour]),
                        forecast_error=(actual[day,hour]-predictions[day,m,hour])/unit,
                        margin=margin/unit,deficit_without_startup=max(0,truth-no_delay)))
    hourly=pd.DataFrame(rows);test=hourly[hourly.phase.eq('test')]
    summaries=[]
    for model,part in test.groupby('model'):
        reference=next(r for r in report['models'] if r['model']==model)
        deficit=float(part.deficit.sum());demand=float(part.demand.sum())
        np.testing.assert_allclose(part.units.sum(),reference['unit_hours'])
        np.testing.assert_allclose(deficit/demand,reference['deficit_fraction'])
        by_series=part.groupby('series').deficit.sum().sort_values(ascending=False)
        by_day=part.groupby('day').deficit.sum().sort_values(ascending=False)
        top=part.nlargest(max(1,int(np.ceil(len(part)*.01))),'deficit')
        summaries.append(dict(model=model,unit_hours=int(part.units.sum()),deficit_fraction=deficit/demand,
            top_institution=str(by_series.index[0]),top_institution_share=float(by_series.iloc[0]/deficit),
            top_two_institutions_share=float(by_series.iloc[:2].sum()/deficit),
            top_two_days_share=float(by_day.iloc[:2].sum()/deficit),
            worst_one_percent_hours_share=float(top.deficit.sum()/deficit),
            midnight_share=float(part.loc[part.hour.eq(0),'deficit'].sum()/deficit),
            deficit_no_startup=float(part.deficit_without_startup.sum()/demand),
            exceed_calibration_max_hours=int((part.forecast_error>part.margin).sum())))
    hourly.to_csv(OUT/'diagnosis_hourly.csv',index=False)
    test.groupby(['model','series'])[['units','deficit','demand']].sum().to_csv(OUT/'diagnosis_institutions.csv')
    test.groupby(['model','day'])[['units','deficit','demand']].sum().to_csv(OUT/'diagnosis_days.csv')
    test.groupby(['model','hour'])[['units','deficit','demand']].sum().to_csv(OUT/'diagnosis_hours.csv')
    test.sort_values('deficit',ascending=False).groupby('model').head(20).to_csv(OUT/'diagnosis_extremes.csv',index=False)
    (OUT/'diagnosis.json').write_text(json.dumps(dict(original_totals_reproduced=True,models=summaries),indent=2))
    print(json.dumps([r for r in summaries if r['model'] in ['28M','ets','weekly_mean']],indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase')
    args=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    globals()[args.phase]()
