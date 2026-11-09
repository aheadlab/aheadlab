"""Recompute a systematic forecast sample locally using the pinned 5M weights."""
import hashlib,json,resource,time
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from timestral import TimestralForecaster
from carbonshift.core import choose_window

ROOT=Path(__file__).resolve().parents[1];RAW=ROOT/'data/raw';OUT=ROOT/'results'
REVISION='bdd20cfc15a3fea0e4cb5ccef37f8d3ca7aa335f'
ZONES=['NO1','NO4','SE1','SE2','SE3','SE4']
def main():
    torch.set_num_threads(1);torch.manual_seed(0)
    data=pd.read_parquet(next(RAW.glob('data/*.parquet')))
    saved=pd.read_parquet(next(RAW.glob('predictions/PRED-Timestral-5M_*.parquet')),columns=['split','zone','origin','h','point'])
    hist={(s,z):f.set_index('time').ci_g_per_kwh.sort_index() for (s,z),f in data.groupby(['split','zone'])}
    cache=Path('/home/app/.cache/huggingface/hub/models--mistralai--Timestral-5M/snapshots')/REVISION
    start=time.perf_counter();model=TimestralForecaster.from_pretrained(str(cache),device='cpu',max_context=8192)
    load_seconds=time.perf_counter()-start;rows=[]
    dates=[('retro',d) for d in ['2025-07-05','2025-10-01','2025-12-27']]+[('holdout','2026-10-16')]
    for split,date in dates:
        origin=pd.Timestamp(date,tz='UTC')
        for zone in ZONES:
            x=hist[(split,zone)].loc[:origin].to_numpy()[-8192:]
            assert x.shape==(8192,) and np.isfinite(x).all()
            before=hashlib.sha256(x.tobytes()).hexdigest();start=time.perf_counter()
            result=model.forecast(x.astype(np.float32),prediction_length=96)
            seconds=time.perf_counter()-start
            point=np.asarray(result.quantile(.5)).reshape(-1)
            reference=saved[saved.split.eq(split)&saved.zone.eq(zone)&saved.origin.eq(origin)].sort_values('h').point.to_numpy()
            assert reference.shape==point.shape==(96,)
            difference=float(np.abs(point-reference).max())
            rows.append(dict(split=split,zone=zone,origin=date,max_abs_difference=difference,seconds=seconds,
                same_window=choose_window(np.maximum(point,0))['start']==choose_window(np.maximum(reference,0))['start']))
            assert hashlib.sha256(x.tobytes()).hexdigest()==before
        print('Reproduced',date,flush=True)
    report=dict(model='Timestral-5M',revision=REVISION,context=8192,forecasts=len(rows),rows=rows,
        max_abs_difference=max(r['max_abs_difference'] for r in rows),same_windows=sum(r['same_window'] for r in rows),
        median_seconds=float(np.median([r['seconds'] for r in rows])),load_seconds=load_seconds,
        peak_process_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
        tolerance_g_per_kwh=.001)
    report['passed']=bool(report['max_abs_difference']<=.001 and report['same_windows']==len(rows))
    (OUT/'local_reproduction.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
    if not report['passed']:raise ValueError('Local reproduction differs; investigate before claiming equivalence')
if __name__=='__main__':main()
