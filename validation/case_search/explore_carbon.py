"""Development-only scheduling analysis: January-June 2025, no final scoring."""
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path('/workspace/validation/case_search/carbon_source');OUT=Path('/out')
END=pd.Timestamp('2025-07-01',tz='UTC')
columns=['zone','split','origin','h','target_time','actual','point']
frames={}
for path in ROOT.glob('predictions/*.parquet'):
    name=path.name.split('_KHEPRI')[0].removeprefix('PRED-')
    cols=columns+(['q'+f'{q:.2f}' for q in [.01,*np.arange(.05,1,.05),.99]] if name=='Timestral-5M' else [])
    frames[name]=pd.read_parquet(path,columns=cols,filters=[('split','==','retro'),('origin','<',END)])
ci=pd.read_parquet(next(ROOT.glob('data/*.parquet')),filters=[('split','==','retro'),('time','<',END)])
histories={z:f.set_index('time').ci_g_per_kwh.sort_index() for z,f in ci.groupby('zone')}
keys=['zone','origin','h'];base=frames['Timestral-5M'].set_index(keys).sort_index()
for name,f in frames.items():
    frame=f.set_index(keys).sort_index()
    assert frame.index.equals(base.index)
    np.testing.assert_allclose(frame.actual,base.actual)
    frames[name]=frame
rows=[]
for (zone,origin),target in base.groupby(level=[0,1]):
    assert np.array_equal(target.index.get_level_values('h'),np.arange(1,97))
    actual=target.actual.to_numpy();past=histories[zone].loc[:origin]
    profiles={name:f.loc[(zone,origin),'point'].to_numpy() for name,f in frames.items()}
    qcols=[c for c in target if c.startswith('q')];qlevels=np.array([float(c[1:]) for c in qcols])
    qs=target[qcols].to_numpy()
    profiles['Timestral-5M-mean']=np.trapezoid(qs,qlevels,axis=1)+.01*(qs[:,0]+qs[:,-1])
    future=pd.date_range(origin+pd.Timedelta(hours=1),periods=96,freq='h')
    profiles['yesterday']=past.reindex(future[:24]-pd.Timedelta(days=1)).to_numpy()
    profiles['yesterday']=np.resize(profiles['yesterday'],96)
    recent=past.iloc[-28*24:];hourly=recent.groupby(recent.index.hour).mean()
    profiles['hourly_mean']=hourly.reindex(future.hour).to_numpy()
    profiles['immediate']=np.arange(96,dtype=float)
    for horizon in [24,48,96]:
        for duration in [2,4,8]:
            windows=np.arange(horizon-duration+1)[:,None]+np.arange(duration)
            actual_windows=actual[windows].mean(axis=1);oracle=float(actual_windows.min())
            for name,pred in profiles.items():
                assert np.isfinite(pred).all()
                chosen=int(np.argmin(pred[windows].mean(axis=1)))
                rows.append(dict(zone=zone,origin=str(origin),horizon=horizon,duration=duration,model=name,
                    actual_ci=float(actual_windows[chosen]),regret=float(actual_windows[chosen]-oracle),delay_hours=chosen))
table=pd.DataFrame(rows)
table.groupby(['horizon','duration','model'])[['actual_ci','regret','delay_hours']].mean().to_csv(OUT/'carbon_screening.csv')
print(table.groupby(['horizon','duration','model'])[['actual_ci','regret']].mean().to_string())
