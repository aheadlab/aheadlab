"""Development-only decision screening on already-observed V2 forecasts."""
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path('/workspace')
CAP=ROOT/'capacityplanner'
OUT=Path('/out')
MODELS=['last','daily','weekly','weekly_mean','ets','mstl','ridge','5M','28M']
data=pd.read_parquet(CAP/'data/processed/v2/selected.parquet')
manifest=json.loads((CAP/'results/capacity-v2/protocol.json').read_text())
first=data.index.get_loc(pd.Timestamp('2025-12-08',tz='UTC'))
rows=[]
for series in data:
    with np.load(CAP/'data/processed/v2/forecasts'/f'{series}-{manifest["fingerprint"][:16]}.npz') as cache:
        predictions=cache['median']
    y=data[series].to_numpy();actual=y[first:].reshape(-1,24)
    scale=max(float(np.nanmean(y[:first])),1e-9)
    for duration in [1,2,4]:
        for allowed,label in [(range(25-duration),'all_day'),(range(7-duration),'night_utc')]:
            starts=np.array(list(allowed));offsets=starts[:,None]+np.arange(duration)
            for day in range(28,len(actual)):
                truth=actual[day];past=y[:first+day*24]
                if not np.isfinite(truth).all():continue
                profiles={m:predictions[day,i] for i,m in enumerate(MODELS)}
                history=past[-28*24:].reshape(-1,24)
                profiles['hourly_mean']=np.nanmean(history,axis=0)
                profiles['hourly_median']=np.nanmedian(history,axis=0)
                for name,profile in profiles.items():
                    start=int(starts[np.argmin(profile[offsets].sum(axis=1))])
                    value=float(truth[start:start+duration].sum())
                    rows.append(dict(series=series,day=day,duration=duration,allowed=label,model=name,
                        start=start,traffic=value,normalized_traffic=value/scale,
                        oracle=float(truth[offsets].sum(axis=1).min())/scale))
                fixed=2 if 2 in starts else int(starts[0])
                value=float(truth[fixed:fixed+duration].sum())
                rows.append(dict(series=series,day=day,duration=duration,allowed=label,model='fixed_02utc',
                    start=fixed,traffic=value,normalized_traffic=value/scale,
                    oracle=float(truth[offsets].sum(axis=1).min())/scale))
table=pd.DataFrame(rows)
summary=table.groupby(['duration','allowed','model'])[['normalized_traffic','traffic','oracle']].mean()
summary['normalized_regret']=summary.normalized_traffic-summary.oracle
summary.to_csv(OUT/'window_screening.csv')
print(summary.to_string())
