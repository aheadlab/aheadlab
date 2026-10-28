"""Public simulated PVGIS and Open-Meteo data, raw request-addressed cache."""
import hashlib
import json
from pathlib import Path
import pandas as pd
import requests
from .prepare import validate_index, unisci

VARIABLES = 'shortwave_radiation,direct_radiation,diffuse_radiation,cloud_cover,temperature_2m'


def cache_path(url, params, cache_dir='data/raw'):
    key = json.dumps([url, params], sort_keys=True, separators=(',', ':'))
    return Path(cache_dir) / (hashlib.sha256(key.encode()).hexdigest() + '.json')


def _get(url, params, cache_dir, timeout):
    path = cache_path(url, params, cache_dir)
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    response = requests.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding='utf-8')
    return data


def scarica_pvgis(lat, lon, anno_inizio, anno_fine, angle=30, aspect=0, loss=14, cache_dir='data/raw'):
    params = dict(lat=lat, lon=lon, peakpower=1, loss=loss, pvcalculation=1,
                  angle=angle, aspect=aspect, startyear=anno_inizio, endyear=anno_fine, outputformat='json')
    data = _get('https://re.jrc.ec.europa.eu/api/v5_3/seriescalc', params, cache_dir, 120)
    rows = pd.DataFrame(data['outputs']['hourly'])
    index = pd.DatetimeIndex(pd.to_datetime(rows.time, format='%Y%m%d:%H%M', utc=True)).floor('h')
    validate_index(index, False)
    return pd.DataFrame({'kwh': pd.to_numeric(rows.P).to_numpy() / 1000}, index=index).asfreq('h')


def _weather(url, params, cache_dir, timeout):
    data = _get(url, params, cache_dir, timeout)
    frame = pd.DataFrame(data['hourly'])
    frame.index = pd.DatetimeIndex(pd.to_datetime(frame.pop('time'), utc=True))
    validate_index(frame.index, False)
    return frame.asfreq('h')


def scarica_meteo_storico(lat, lon, inizio, fine, cache_dir='data/raw'):
    return _weather('https://archive-api.open-meteo.com/v1/archive', dict(latitude=lat, longitude=lon,
        start_date=str(inizio), end_date=str(fine), hourly=VARIABLES, timezone='UTC'), cache_dir, 120)


def scarica_meteo_previsto(lat, lon, giorni=3, cache_dir='data/raw'):
    # Date in cache key prevents an old forecast being served as today's forecast.
    today = pd.Timestamp.now(tz='UTC').date()
    return _weather('https://api.open-meteo.com/v1/forecast', dict(latitude=lat, longitude=lon,
        start_date=str(today), end_date=str(today + pd.Timedelta(days=giorni-1)),
        hourly=VARIABLES, timezone='UTC'), cache_dir, 60)


def historical_dataset(lat=45.82, lon=8.83, year=2023, angle=30, aspect=0, loss=14, cache_dir='data/raw'):
    parts = []
    for y in (year-1, year):
        pv = scarica_pvgis(lat, lon, y, y, angle, aspect, loss, cache_dir)
        weather = scarica_meteo_storico(lat, lon, f'{y}-01-01', f'{y}-12-31', cache_dir)
        parts.append(unisci(pv, weather))
    return pd.concat(parts)
