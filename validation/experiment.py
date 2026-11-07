"""Offline experiments, deliberately independent of application behavior."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd

ROOT = Path('/workspace')
OUT = Path('/out')
for project in ('stocksense', 'cloudguard', 'solarcast'):
    sys.path.insert(0, str(ROOT / project / 'src'))


def save(frame, name):
    frame.to_csv(OUT / f'{name}.csv', index=False)


def interval(values, block=1, repetitions=2000):
    """Circular block bootstrap of ordered paired differences, fixed seed."""
    values = np.asarray(values, float)
    rng = np.random.default_rng(20261105)
    starts = rng.integers(len(values), size=(repetitions, int(np.ceil(len(values)/block))))
    indices = (starts[..., None] + np.arange(block)) % len(values)
    draws = values[indices.reshape(repetitions, -1)[:, :len(values)]].mean(axis=1)
    return dict(mean=float(values.mean()), low=float(np.quantile(draws, .025)),
                high=float(np.quantile(draws, .975)), n=len(values), block=block)


def audit():
    rows = []
    for size in ('5M', '28M', '209M'):
        f = pd.read_csv(ROOT / f'stocksense/results/uci-{size}/backtest.csv')
        p = f.pivot(index=['sku', 'fold'], columns='modello', values='mae')
        delta = p.auto_ets-p[size]
        # Resample products with all their folds retained, not 400 independent rows.
        rows.append(dict(model=size, **interval(delta.groupby(level='sku').mean()),
                         wins=int((delta > 1e-9).sum()), ties=int((delta.abs() <= 1e-9).sum()),
                         caveat='SKU-cluster only; shared retailer shocks remain'))
    save(pd.DataFrame(rows), 'stock_existing_paired')
    if (OUT/'stock_new_scores.csv').exists():
        f = pd.read_csv(OUT/'stock_new_scores.csv')
        rows = []
        for metric in ('mae','cumulative_abs_error','signed_error'):
            p = f.pivot(index=['sku','fold'], columns='model', values=metric)
            for baseline in ('auto_ets','rolling_median','croston_sba'):
                delta = p[baseline]-p['5M']
                rows.append(dict(metric=metric, baseline=baseline,
                    **interval(delta.groupby(level='sku').mean()),
                    positive='favors 5M for absolute errors; signed error is descriptive'))
        save(pd.DataFrame(rows), 'stock_new_paired')
    f = pd.read_csv(ROOT/'solarcast/results/pvgis-5M/daily.csv')
    f['lead_day'] = (pd.to_datetime(f.day)-pd.to_datetime(f.origin)).dt.days+1
    rows = []
    for lead in (1, 2):
        for metric in ('daily_energy_mae', 'daytime_mae'):
            p = f[f.lead_day.eq(lead)].pivot(index='origin', columns='method', values=metric).sort_index()
            for block in (7, 28):
                rows.append(dict(lead_day=lead, metric=metric,
                    **interval(p.radiation_regression-p.B, block),
                    sign='positive favors B; daytime metric here equally weights days'))
    save(pd.DataFrame(rows), 'solar_existing_paired')
    f = pd.read_csv(ROOT/'cloudguard/results/timestral-full/anomaly_days.csv')
    events = pd.read_csv(ROOT/'cloudguard/results/timestral-full/events.csv')
    f['data'] = pd.to_datetime(f.data)
    rows = []
    for model, group in f.groupby('modello'):
        for e in events.itertuples():
            start = pd.Timestamp(e.inizio)
            days = group[(group.servizio == e.servizio) & (group.data >= start)
                         & (group.data < start+pd.Timedelta(days=e.giorni))]
            if days.empty:
                continue
            alerts = days[days.anomalia.astype(str).str.lower().eq('true')]
            rows.append(dict(model=model, event=e.evento, evaluated_days=len(days),
                detected=not alerts.empty,
                delay_days=(alerts.data.min()-start).days if len(alerts) else np.nan))
    save(pd.DataFrame(rows), 'cloud_event_delays')


def stock():
    from stocksense.prepare import pulisci, vendite_giornaliere, winsorize_training
    from stocksense.backtest import origins
    from stocksense.forecast_all import forecast
    from stocksense.demo import simulated_stock
    from stocksense import forecaster
    from statsforecast.models import CrostonSBA
    from timestral import TimestralForecaster
    start_time = time.time()
    # Load the exact snapshot already used by the original 5M benchmark.
    revision = 'bdd20cfc15a3fea0e4cb5ccef37f8d3ca7aa335f'
    snapshot = Path(os.environ['HF_HOME'])/'hub/models--mistralai--Timestral-5M/snapshots'/revision
    if not snapshot.is_dir():
        raise RuntimeError(f'Required model snapshot unavailable: {snapshot}')
    model = TimestralForecaster.from_pretrained(str(snapshot), device='cpu')
    forecaster.carica_modello = lambda size: model
    raw = ROOT/'stocksense/data/raw/online_retail_II.xlsx'
    cached = ROOT/'stocksense/data/processed/transazioni.parquet'
    digest = hashlib.sha256(raw.read_bytes()).hexdigest()
    manifest = json.loads(cached.with_suffix('.json').read_text())
    assert digest == manifest['sha256'], 'Stale transaction cache'
    frame = pulisci(pd.read_parquet(cached))
    calendar = pd.date_range(frame.giorno.min(), frame.giorno.max())
    first = min(origins(len(calendar))[0], len(calendar)-180)
    daily = vendite_giornaliere(frame, 50, calendar[first])
    del frame
    methods = ['5M', 'auto_ets', 'rolling_median', 'croston_sba']
    scores, ledgers, calibrations = [], [], []
    levels = [.5, .8, .9]
    start = len(daily)-180
    initial = simulated_stock(daily.iloc[:start])
    for index, sku in enumerate(daily):
        values = daily[sku].to_numpy()
        cache = {}
        def predict(method, cutoff, h):
            key = (method, cutoff, h)
            if key not in cache:
                history = values[:cutoff]
                if method == 'rolling_median':
                    result = np.full(h, np.median(winsorize_training(history)[-28:]))
                elif method == 'croston_sba':
                    result = CrostonSBA().forecast(y=winsorize_training(history), h=h)['mean']
                else:
                    result = forecast(history, h, method).mediana
                cache[key] = np.maximum(result, 0)
            return cache[key]
        for method in methods:
            for fold, cutoff in enumerate(origins(len(daily))):
                p = predict(method, cutoff, 30)
                scores.append(dict(sku=sku, fold=fold, model=method,
                    mae=float(np.abs(values[cutoff:cutoff+30]-p).mean()),
                    signed_error=float((p-values[cutoff:cutoff+30]).mean()),
                    cumulative_abs_error=float(abs(p.sum()-values[cutoff:cutoff+30].sum()))))
            residuals = []
            for cutoff in range(start-6*21, start, 21):
                residuals.append(values[cutoff:cutoff+21].sum()-predict(method, cutoff, 21).sum())
            for level in levels:
                # Equal rule for ALL models, including 5M: point sum + calibrated error.
                safety = max(0., float(np.quantile(residuals, level)))
                calibrations.append(dict(sku=sku, model=method, level=level,
                                         adjustment=safety, calibration_windows=6))
                stock_value = float(initial[sku])
                pending = []
                for t in range(start, len(daily)):
                    stock_value += sum(q for due, q in pending if due == t)
                    pending = [(due, q) for due, q in pending if due > t]
                    order = 0
                    if (t-start) % 7 == 0:
                        target = predict(method, t, 21).sum()+safety
                        order = max(0, int(np.ceil(target-stock_value-sum(q for _, q in pending))))
                        if order:
                            pending.append((t+14, order))
                    demand = values[t]
                    sold = min(stock_value, demand)
                    stock_value -= sold
                    ledgers.append(dict(sku=sku, model=method, level=level,
                        date=str(daily.index[t].date()), lost=demand-sold,
                        demand=demand, inventory=stock_value, order=order))
        print(f'StockSense {index+1}/50 SKU; {time.time()-start_time:.0f}s', flush=True)
    scores = pd.DataFrame(scores)
    save(scores, 'stock_new_scores')
    save(scores.groupby('model', as_index=False)[['mae','signed_error','cumulative_abs_error']].mean(), 'stock_new_accuracy')
    ledger = pd.DataFrame(ledgers)
    save(ledger, 'stock_equal_policy_ledger')
    summary = ledger.groupby(['model', 'level'], as_index=False).agg(
        lost=('lost','sum'), demand=('demand','sum'), inventory=('inventory','mean'))
    summary['fill_rate'] = 1-summary.lost/summary.demand
    summary['dominated'] = [bool(((summary.inventory <= r.inventory) & (summary.lost <= r.lost)
        & ((summary.inventory < r.inventory) | (summary.lost < r.lost))).any()) for r in summary.itertuples()]
    save(summary, 'stock_equal_policy_summary')
    save(pd.DataFrame(calibrations), 'stock_calibration')
    original = pd.read_csv(ROOT/'stocksense/results/uci-5M/backtest.csv', dtype={'sku':str})
    reproduced = scores[scores.model.eq('5M')].merge(original[original.modello.eq('5M')], on=['sku','fold'])
    (OUT/'stock_metadata.json').write_text(json.dumps(dict(
        source_sha256=digest, parquet_sha256=hashlib.sha256(cached.read_bytes()).hexdigest(),
        revision=revision, skus=50, folds=8, simulation_days=180, calibration_windows=6,
        quantiles=levels, lead_time=14, cycle=7, elapsed_seconds=time.time()-start_time,
        reproduced_pairs=len(reproduced), max_mae_difference=float(abs(reproduced.mae_x-reproduced.mae_y).max()),
        caveat='Exploratory known dataset; frozen six-window calibration; not a prospective ROI estimate'), indent=2))


def cloud():
    from cloudguard import forecaster
    from cloudguard.backtest import benchmark_forecast, benchmark_anomalies
    from timestral import TimestralForecaster
    revision = 'bdd20cfc15a3fea0e4cb5ccef37f8d3ca7aa335f'
    snapshot = Path(os.environ['HF_HOME'])/'hub/models--mistralai--Timestral-5M/snapshots'/revision
    model = TimestralForecaster.from_pretrained(str(snapshot), device='cpu')
    forecaster.carica_modello = lambda size: model
    forecasts, summaries, details, event_rows, delay_rows = [], [], [], [], []
    dates = pd.date_range('2025-01-01', periods=360)
    for seed in (7,17,29):
        rng = np.random.default_rng(seed)
        series, events = {}, []
        for service, base in [('small',10),('medium',30),('large',60)]:
            t = np.arange(360)
            values = (base+.015*t)*(1-.15*(dates.day_of_week >= 5))*rng.lognormal(0,.07,360)
            # Unexpected short excess, then gradual avoidable excess.
            values[140:143] *= 1.7
            values[210:231] *= 1+np.linspace(.05,.45,21)
            # Planned permanent capacity increase: not an incident. Deliberately
            # not passed as a covariate; measures the limits of history-only alerts.
            values[280:] *= 1.25
            series[service] = values
            for label, start, duration in [('spike',140,3),('drift',210,21)]:
                events.append(dict(evento=f'{service}-{label}', servizio=service,
                                   inizio=dates[start], giorni=duration, kind=label))
        table, truth = pd.DataFrame(series, index=dates), pd.DataFrame(events)
        scores = benchmark_forecast(table, model='5M', folds=8)
        summary, detail = benchmark_anomalies(table, truth, model='5M', days=260)
        forecasts.append(scores.assign(seed=seed))
        summaries.append(summary.assign(seed=seed))
        details.append(detail.assign(seed=seed))
        event_rows.append(truth.assign(seed=seed))
        for method, group in detail.groupby('modello'):
            for event in truth.itertuples():
                days = group[(group.servizio == event.servizio) & (group.data >= event.inizio)
                    & (group.data < event.inizio+pd.Timedelta(days=event.giorni))]
                alerts = days[days.anomalia]
                delay_rows.append(dict(seed=seed, model=method, event=event.evento, kind=event.kind,
                    detected=len(alerts)>0, delay_days=(alerts.data.min()-event.inizio).days if len(alerts) else np.nan))
        print(f'CloudGuard seed {seed} complete', flush=True)
    save(pd.concat(forecasts), 'cloud_extended_forecasts')
    save(pd.concat(summaries), 'cloud_extended_anomalies')
    save(pd.concat(details), 'cloud_extended_days')
    save(pd.concat(event_rows), 'cloud_extended_events')
    save(pd.DataFrame(delay_rows), 'cloud_extended_delays')
    (OUT/'cloud_metadata.json').write_text(json.dumps(dict(revision=revision,
        seeds=[7,17,29], services=3, days=360, anomaly_days=260,
        scenarios='1.7x spike 3d; 5-45% ramp 21d; legitimate 25% permanent step at day 280',
        limitation='Synthetic stress test; legitimate step not supplied to either detector; minimum excess 5 USD'),indent=2))


def solar():
    from solarcast.ingest import historical_dataset
    os.chdir(ROOT/'solarcast')
    data = historical_dataset()
    rows = []
    cols = ['shortwave_radiation', 'cloud_cover', 'temperature_2m']
    variants = {'radiation_720': (['shortwave_radiation'],720),
                'all_720': (cols,720), 'radiation_8784': (['shortwave_radiation'],8784),
                'all_8784': (cols,8784)}
    for origin in pd.date_range('2023-01-01', '2023-12-30', tz='UTC'):
        future = data.loc[origin:origin+pd.Timedelta(hours=47)]
        for variant, (features, context) in variants.items():
            train = data[data.index < origin].iloc[-context:]
            x = np.column_stack([train[features].to_numpy(), np.ones(len(train))])
            y = train.kwh.to_numpy()
            valid = np.isfinite(x).all(axis=1) & np.isfinite(y)
            coef = np.linalg.lstsq(x[valid], y[valid], rcond=None)[0]
            pred = np.maximum(np.column_stack([future[features], np.ones(len(future))]) @ coef, 0)
            for lead in (1, 2):
                actual = future.iloc[(lead-1)*24:lead*24]
                p = pred[(lead-1)*24:lead*24]
                light = actual.shortwave_radiation.to_numpy() > 0
                rows.append(dict(variant=variant, origin=origin.isoformat(), lead_day=lead,
                    daily_energy_mae=abs(actual.kwh.sum()-p.sum()),
                    daytime_mae=np.abs(actual.kwh.to_numpy()-p)[light].mean(), daytime_n=int(light.sum())))
    frame = pd.DataFrame(rows)
    save(frame, 'solar_matched_regression')
    existing = pd.read_csv(ROOT/'solarcast/results/pvgis-5M/daily.csv')
    existing = existing[existing.method.eq('B')].copy()
    existing['lead_day'] = (pd.to_datetime(existing.day)-pd.to_datetime(existing.origin)).dt.days+1
    rows = []
    for variant in variants:
        matched = frame[frame.variant.eq(variant)].merge(existing, on=['origin','lead_day'], suffixes=('_reg','_B'), validate='one_to_one')
        assert len(matched) == 728
        for lead in (1, 2):
            part = matched[matched.lead_day.eq(lead)].sort_values('origin')
            for metric in ('daily_energy_mae','daytime_mae'):
                for block in (7,28):
                    rows.append(dict(variant=variant, lead_day=lead, metric=metric,
                        **interval(part[f'{metric}_reg']-part[f'{metric}_B'], block)))
    save(pd.DataFrame(rows), 'solar_matched_paired')
    save(pd.DataFrame([dict(method=variant, daily_energy_mae=group.daily_energy_mae.mean(),
        daytime_mae=np.average(group.daytime_mae, weights=group.daytime_n))
        for variant,group in frame.groupby('variant')]), 'solar_matched_summary')
    baseline = pd.read_csv(ROOT/'solarcast/results/pvgis-5M/daily.csv')
    baseline = baseline[baseline.method.eq('radiation_regression')].sort_values(['origin','day'])
    reproduction = frame[frame.variant.eq('radiation_720')].sort_values(['origin','lead_day'])
    assert np.allclose(reproduction.daily_energy_mae, baseline.daily_energy_mae, atol=1e-10)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['audit','stock','solar','cloud'])
    phase = parser.parse_args().phase
    OUT.mkdir(exist_ok=True)
    globals()[phase]()
    import importlib.metadata
    versions = {}
    for package in ('numpy','pandas','torch','timestral','statsforecast'):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            pass
    fingerprints = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for project in ('stocksense','solarcast','cloudguard')
        for p in (ROOT/project/'src').rglob('*.py')}
    (OUT/f'{phase}_environment.json').write_text(json.dumps(dict(versions=versions,
        source_sha256=fingerprints, experiment_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2))
