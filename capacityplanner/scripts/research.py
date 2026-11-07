"""Frozen exploratory protocol and official-source preparation."""
import argparse
import hashlib
import json
from pathlib import Path
import os
import time
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = Path('/out') if Path('/out').is_dir() else ROOT/'results/cesnet'


def inspect():
    import tables
    with tables.open_file(ROOT/'data/raw/institutions-hour.h5',mode='r') as file:
        print(file,flush=True)
        for node in file.walk_nodes():
            print(node._v_pathname, type(node).__name__, getattr(node,'shape',''),flush=True)
            if hasattr(node,'colnames'):
                print(node.colnames, node[:2],flush=True)
            for name in node._v_attrs._f_list('user'):
                print('ATTR',name,str(node._v_attrs[name])[:1500],flush=True)


def prepare():
    """Sample on the training prefix only; retain missing targets as NaN."""
    import tables
    from capacityplanner.benchmark import SEED
    source = json.loads((ROOT/'data/source.json').read_text())
    raw = ROOT/'data/raw/institutions-hour.h5'
    digest = hashlib.sha256()
    with raw.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    if digest.hexdigest() != source['sha256']:
        raise ValueError('Raw dataset checksum changed')
    with tables.open_file(raw, mode='r') as file:
        timestamps = pd.DataFrame.from_records(file.root.times.times_1_hour[:])
        timestamps['timestamp'] = pd.to_datetime(timestamps['time'], unit='s', utc=True)
        mapping = timestamps.set_index('id_time')['timestamp']
        if mapping.index.has_duplicates or mapping.duplicated().any():
            raise ValueError('Duplicate time identifiers')
        start = mapping.min().ceil('D')
        stop = (mapping.max()+pd.Timedelta(hours=1)).floor('D')
        hours = pd.date_range(start, stop, freq='h', inclusive='left')
        table = file.root.institutions.agg_1_hour
        records = pd.DataFrame({name:table.col(name) for name in ['id_institution','id_time','n_bytes']})
    records['timestamp'] = records.id_time.map(mapping)
    if records.timestamp.isna().any() or records.duplicated(['id_institution','timestamp']).any():
        raise ValueError('Invalid observation time identifiers')
    records['mbps'] = records.n_bytes.astype(float)*8/3600/1e6
    if not np.isfinite(records.mbps).all() or (records.mbps<0).any():
        raise ValueError('Invalid measured byte counts')
    frame = records.pivot(index='timestamp',columns='id_institution',values='mbps').reindex(hours)
    first = len(frame)-56*24
    training = frame.iloc[:first]
    eligible = sorted(int(s) for s in frame if training[s].notna().mean()>=.95 and training[s].gt(0).mean()>=.5)
    selected = sorted(np.random.default_rng(SEED).choice(eligible,size=12,replace=False).tolist())
    output = frame[selected].copy()
    output.columns = output.columns.astype(str)
    destination = ROOT/'data/processed'
    destination.mkdir(parents=True,exist_ok=True)
    output.to_parquet(destination/'selected.parquet')
    metadata = dict(source=source,seed=SEED,selected_ids=selected,eligible_count=len(eligible),
        eligibility='training coverage >=95%; positive traffic >=50% of training hours',
        start=str(hours[0]),end=str(hours[-1]),hours=len(hours),training_hours=first,
        calibration_start=str(hours[first]),selection_start=str(hours[first+14*24]),
        test_start=str(hours[first+28*24]),time_basis='UTC Unix seconds; complete UTC calendar days',
        missing_policy='absent HDF5 rows or hours remain NaN; observed zero remains zero',
        training_coverage={str(s):float(training[s].notna().mean()) for s in selected},
        missing_hours={s:int(output[s].isna().sum()) for s in output},
        values_sha256=hashlib.sha256(output.to_numpy().tobytes()).hexdigest())
    (destination/'selection.json').write_text(json.dumps(metadata,indent=2))
    (OUT/'data_selection.json').write_text(json.dumps(metadata,indent=2))
    print(json.dumps(metadata,indent=2),flush=True)


def benchmark():
    from capacityplanner.benchmark import run
    run(ROOT, OUT)


def analyze():
    from analyze_results import run
    run(ROOT, OUT)


def environment():
    import importlib.metadata
    import platform
    packages={d.metadata['Name']:d.version for d in importlib.metadata.distributions()}
    result=dict(python=platform.python_version(),platform=platform.platform(),
                packages=dict(sorted(packages.items())))
    (OUT/'validation_environment.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:packages[k] for k in ['numpy','pandas','statsforecast','torch','timestral']},indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=['inspect','prepare','benchmark','analyze','environment'])
    args=parser.parse_args()
    globals()[args.phase]()
