"""Daily rolling 48h retrospective evaluation; no fit sees the future."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from .forecast import forecast
from .prepare import validate_index


def run_backtest(data, model='baseline', quick=False, max_context=None, source='synthetic'):
    validate_index(data.index)
    year = data.index[-1].year
    context = max_context if max_context is not None else (720 if quick else 8784)
    origins = pd.date_range(f'{year}-01-01', f'{year}-12-30', freq='D', tz='UTC')
    if quick:
        origins = pd.DatetimeIndex([pd.Timestamp(f'{year}-{m:02d}-15', tz='UTC') for m in (1,4,7,10)])
    methods = ['seasonal_naive24', 'radiation_regression'] + ([] if model == 'baseline' else ['A', 'B'])
    rows = []
    for origin in origins:
        history = data.loc[data.index < origin]
        future = data.loc[origin:origin+pd.Timedelta(hours=47)]
        if len(future) != 48:
            raise ValueError('Each origin requires 48 actual hours')
        for method in methods:
            pred = forecast(history, future.drop(columns='kwh'), method,
                            '5M' if model == 'baseline' else model, context)
            for day, actual in future.groupby(future.index.floor('D')):
                p = pred.frame.loc[actual.index]
                valid = np.isfinite(actual.kwh) & np.isfinite(p['median'])
                daylight = valid & (actual.shortwave_radiation > 0)
                error = abs(actual.kwh-p['median'])
                daily = abs(actual.kwh.sum()-p['median'].sum()) if valid.all() else np.nan
                coverage = np.nan
                if 'p10' in p and valid.any():
                    coverage = ((actual.kwh[valid] >= p.p10[valid]) & (actual.kwh[valid] <= p.p90[valid])).mean()
                cloud = actual.cloud_cover.mean()
                rows.append(dict(origin=origin.isoformat(), day=day.isoformat(), method=method,
                    season={12:'winter',1:'winter',2:'winter',3:'spring',4:'spring',5:'spring',6:'summer',7:'summer',8:'summer',9:'autumn',10:'autumn',11:'autumn'}[day.month],
                    sky='missing' if pd.isna(cloud) else ('clear' if cloud < 30 else 'cloudy' if cloud > 70 else 'variable'),
                    daily_energy_mae=daily, daytime_mae=error[daylight].mean(), coverage=coverage,
                    daytime_n=int(daylight.sum()), valid_n=int(valid.sum()), context_used=pred.metadata['context_used'],
                    weather=pred.metadata['weather']))
    daily = pd.DataFrame(rows)
    summary = []
    for grouping in (['method'], ['method', 'season'], ['method', 'sky']):
        for key, group in daily.groupby(grouping):
            key = key if isinstance(key, tuple) else (key,)
            entry = dict(zip(grouping, key))
            entry.update(group='overall' if len(grouping)==1 else grouping[1],
                daily_energy_mae=group.daily_energy_mae.mean(),
                daytime_mae=np.average(group.daytime_mae.fillna(0), weights=group.daytime_n) if group.daytime_n.sum() else np.nan,
                coverage=np.average(group.coverage.fillna(0), weights=group.valid_n) if group.coverage.notna().any() else np.nan,
                forecast_days=len(group))
            summary.append(entry)
    meta = dict(source=source, model=model, quick=quick, max_context=context, origins=len(origins),
        first_origin=str(origins[0]), last_origin=str(origins[-1]), horizon=48,
        units='kWh/kWp', weather_B_C='observed_oracle: optimistic, not operational',
        overlapping_days='Each origin/lead day is evaluated separately',
        end_boundary='Dec 31 origin excluded: next-year observations unavailable',
        context_policy='All available preceding history up to max_context; default full retains previous year',
        daylight='observed shortwave_radiation > 0', missing='hourly finite pairs; daily totals only complete days')
    return daily, pd.DataFrame(summary), meta


def save_results(daily, summary, metadata, output):
    from html import escape
    path = Path(output)
    path.mkdir(parents=True, exist_ok=True)
    daily.to_csv(path/'daily.csv', index=False)
    summary.to_csv(path/'summary.csv', index=False)
    (path/'metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    overall = summary[summary['group']=='overall']
    bars = []
    for i, row in enumerate(overall.itertuples()):
        width = 450*row.daily_energy_mae/max(overall.daily_energy_mae.max(), .001)
        bars.append(f'<text x="10" y="{65+i*45}">{escape(row.method)}</text><rect x="210" y="{50+i*45}" width="{width}" height="20" fill="#e9a23b"/><text x="680" y="{65+i*45}">{row.daily_energy_mae:.3f}</text>')
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="270"><rect width="100%" height="100%" fill="white"/><text x="10" y="25">Daily energy MAE kWh/kWp — '+escape(metadata['source'])+(' SMOKE' if metadata['quick'] else ' retrospective')+'</text>'+''.join(bars)+'</svg>'
    (path/'summary.svg').write_text(svg, encoding='utf-8')
