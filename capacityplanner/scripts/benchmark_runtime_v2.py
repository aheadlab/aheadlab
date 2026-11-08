"""Ancillary local timing/RSS measurements; never used for model selection."""
import argparse
import json
from pathlib import Path
import resource
import statistics
import subprocess
import sys
import time
import pandas as pd
from capacityplanner.core import MODELS,predict

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('/out') if Path('/out').is_dir() else ROOT/'results/capacity-v2'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--model',choices=MODELS)
    args=parser.parse_args()
    if args.model:
        data=pd.read_parquet(ROOT/'data/processed/v2/selected.parquet',columns=['4'])
        y=data.loc[data.index<pd.Timestamp('2025-12-08',tz='UTC'),'4'].to_numpy()[-2016:]
        begin=time.perf_counter();predict(y,args.model);cold=time.perf_counter()-begin
        warm=[]
        for _ in range(10):
            begin=time.perf_counter();predict(y,args.model);warm.append(time.perf_counter()-begin)
        print(json.dumps(dict(model=args.model,first_forecast_seconds=cold,
            warm_median_seconds=statistics.median(warm),warm_min_seconds=min(warm),
            warm_max_seconds=max(warm),peak_process_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)))
        return
    rows=[]
    for model in MODELS:
        output=subprocess.check_output([sys.executable,__file__,'--model',model],text=True)
        row=json.loads(output);rows.append(row);print(json.dumps(row),flush=True)
    pd.DataFrame(rows).to_csv(OUT/'runtime_benchmark.csv',index=False)
    (OUT/'runtime_benchmark.json').write_text(json.dumps(dict(
        description='Ancillary measurement after method/protocol freeze; not used in selection',
        limit='one CPU, 2 GiB, one child at a time, local weights and no network',
        history='institution 4, 2016 hours before 2025-12-08',horizon=24,repetitions=10,
        notes='RSS includes Python and libraries. First forecast includes lazy imports and weight loading; warm calls repeat the same history. Machine-specific, not energy or monetary cost.',
        rows=rows),indent=2))


if __name__=='__main__':main()
