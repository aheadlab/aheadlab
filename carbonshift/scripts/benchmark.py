"""Decision-level evaluation of public Khepri forecasts under a frozen protocol."""
import hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
from carbonshift.core import choose_window,score,paired_interval

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results';RAW=ROOT/'data/raw'
ZONES=['NO1','NO4','SE1','SE2','SE3','SE4'];AI='Timestral-5M'
SOURCE_MODELS=['GBM','SARIMA','snaive_week',AI]
MODELS=SOURCE_MODELS+['yesterday','hourly_mean','fixed_hour','immediate']
DEV_END=pd.Timestamp('2025-07-01',tz='UTC');TEST_START=pd.Timestamp('2025-07-05',tz='UTC')

def dump(name,value):
    (OUT/name).write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')

def sources():
    manifest=json.loads((RAW/'download_manifest.json').read_text())
    for item in manifest['files']:
        digest=hashlib.sha256((RAW/item['path']).read_bytes()).hexdigest()
        if digest!=item['sha256']:raise ValueError('Source changed: '+item['path'])
    return manifest

def main():
    OUT.mkdir(parents=True,exist_ok=True);source=sources()
    names=['docs/PROTOCOL.md','src/carbonshift/core.py','scripts/benchmark.py']
    hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names}
    dump('protocol.json',dict(source=source,hashes=hashes,created_utc=str(pd.Timestamp.now(tz='UTC'))))
    cols=['zone','split','origin','h','target_time','actual','point'];frames={}
    for model in SOURCE_MODELS:
        path=next(RAW.glob(f'predictions/PRED-{model}_*.parquet'))
        frame=pd.read_parquet(path,columns=cols)
        keys=['split','zone','origin','h']
        if frame.duplicated(keys).any():raise ValueError('Duplicate forecast keys')
        if not np.isfinite(frame[['point','actual']].to_numpy()).all() or (frame.actual<0).any():raise ValueError('Invalid values')
        if not (frame.target_time==frame.origin+pd.to_timedelta(frame.h,unit='h')).all():raise ValueError('Invalid horizon timestamps')
        frames[model]=frame.set_index(keys).sort_index()
    base=frames[AI]
    for model,f in frames.items():
        if not f.index.equals(base.index):raise ValueError('Unpaired model files')
        np.testing.assert_allclose(f.actual,base.actual,rtol=0,atol=1e-10)
    data=pd.read_parquet(next(RAW.glob('data/*.parquet')))
    if data.duplicated(['split','zone','time']).any():raise ValueError('Duplicate observations')
    histories={(s,z):f.set_index('time').ci_g_per_kwh.sort_index() for (s,z),f in data.groupby(['split','zone'])}
    for key,history in histories.items():
        if not np.isfinite(history).all() or (history<0).any() or not (history.index.to_series().diff().dropna()==pd.Timedelta(hours=1)).all():
            raise ValueError('Invalid history '+str(key))
    fixed={}
    for zone in data.zone.unique():
        h=histories[('retro',zone)].loc['2024'];hour=h.groupby(h.index.hour).mean()
        means=[sum(hour[(s+i)%24] for i in range(4))/4 for s in range(24)]
        fixed[zone]=int(np.argmin(means))
    cases=[];replays=[];negative_forecasts=0
    # Development decisions are written before any confirmatory score is computed.
    grouped=list(base.groupby(level=[0,1,2]));development=[];rest=[]
    for (split,zone,origin),target in grouped:
        if split=='retro' and origin<DEV_END:development.append(((split,zone,origin),target))
        elif split=='holdout' or origin>=TEST_START:rest.append(((split,zone,origin),target))
    def run(items,phase):
        nonlocal negative_forecasts
        for (split,zone,origin),target in items:
            if not np.array_equal(target.index.get_level_values('h'),np.arange(1,97)):raise ValueError('Missing horizon')
            truth=target.actual.to_numpy();hist=histories[(split,zone)];times=pd.DatetimeIndex(target.target_time)
            np.testing.assert_allclose(hist.reindex(times),truth,rtol=0,atol=1e-10)
            past=hist.loc[:origin]
            profiles={m:frames[m].loc[(split,zone,origin),'point'].to_numpy() for m in SOURCE_MODELS}
            negative_forecasts+=sum(int((v<0).sum()) for v in profiles.values())
            profiles={m:np.maximum(v,0) for m,v in profiles.items()}
            profiles['yesterday']=np.resize(past.reindex(times[:24]-pd.Timedelta(days=1)).to_numpy(),96)
            recent=past.iloc[-28*24:];hourly=recent.groupby(recent.index.hour).mean()
            profiles['hourly_mean']=hourly.reindex(times.hour).to_numpy()
            oracle=choose_window(truth)['expected_ci'];plans={}
            for model in MODELS:
                if model=='fixed_hour':start=int(np.flatnonzero(times.hour==fixed[zone])[0]);expected=None
                elif model=='immediate':start=0;expected=None
                else:
                    plan=choose_window(profiles[model]);start=plan['start'];expected=plan['expected_ci']
                outcome=score(truth,start)
                plans[model]=dict(start=start,stop=start+4,expected_ci=expected,**outcome)
                cases.append(dict(phase=phase if phase=='development' else split,zone=zone,origin=str(origin),model=model,
                    start=start,actual_ci=outcome['actual_ci'],regret=outcome['actual_ci']-oracle,oracle=oracle,
                    delay_hours=start,energy_kwh=100,duration=4))
            if phase!='development' and zone in ZONES and (origin.day==15 or origin==TEST_START or (split=='holdout' and origin.day in [16,23])):
                replays.append(dict(id=zone+'-'+origin.strftime('%Y%m%d'),zone=zone,split=split,origin=str(origin),
                    times=[str(t) for t in times],actual=truth.tolist(),forecasts={m:v.tolist() for m,v in profiles.items()},
                    history=[dict(time=str(t),value=float(v)) for t,v in past.iloc[-168:].items()],plans=plans))
    run(development,'development')
    dev=pd.DataFrame(cases);rank=dev[dev.zone.isin(ZONES)&dev.model.ne(AI)].groupby('model').actual_ci.mean().sort_values()
    classic=str(rank.index[0]);dump('selection.json',dict(ai=AI,classic=classic,development_scores=rank.to_dict(),fixed_hours_utc=fixed))
    print('Selected before test:',AI,'versus',classic,flush=True)
    run(rest,'test');table=pd.DataFrame(cases)
    table.to_csv(OUT/'decisions.csv',index=False)
    summaries=table.groupby(['phase','model'])[['actual_ci','regret','delay_hours']].mean()
    summaries.to_csv(OUT/'all_zones_summary.csv')
    primary=table[table.zone.isin(ZONES)]
    primary.groupby(['phase','model'])[['actual_ci','regret','delay_hours']].mean().to_csv(OUT/'summary.csv')
    primary.groupby(['phase','zone','model'])[['actual_ci','regret','delay_hours']].mean().to_csv(OUT/'zone_summary.csv')
    results={}
    for phase in ['retro','holdout']:
        part=primary[primary.phase.eq(phase)]
        a=part[part.model.eq(AI)].pivot(index='origin',columns='zone',values='actual_ci').sort_index()
        b=part[part.model.eq(classic)].pivot(index='origin',columns='zone',values='actual_ci').reindex(index=a.index,columns=a.columns)
        comparison=paired_interval(a.to_numpy(),b.to_numpy())
        comparison['block14']=paired_interval(a.to_numpy(),b.to_numpy(),block=14)
        comparison.update(ai_ci=float(a.to_numpy().mean()),classic_ci=float(b.to_numpy().mean()),
            days_better=int((a.mean(axis=1)<b.mean(axis=1)-1e-10).sum()),
            zones_better=int((a.mean(axis=0)<b.mean(axis=0)-1e-10).sum()),
            passed=bool(comparison['saving_pct']>=.5 and comparison['ci95'][0]>0))
        results[phase]=comparison
    report=dict(status='complete',ai=AI,classic=classic,zones=ZONES,energy_kwh=100,duration=4,deadline=96,
        results=results,all_jobs_completed=bool(((table.start+4)<=96).all()),negative_forecasts_clipped=negative_forecasts,
        source_commit=source['commit'],replay_count=len(replays),hashes=hashes)
    dump('report.json',report);dump('replays.json',replays)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
