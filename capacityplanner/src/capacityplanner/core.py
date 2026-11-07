"""Past-only forecasting and capacity decisions. No infrastructure mutations."""
from functools import lru_cache
import math
import os
from pathlib import Path
import numpy as np
import pandas as pd

MODELS = ('last', 'daily', 'weekly', 'weekly_mean', 'ets', 'mstl', 'ridge', '5M', '28M')
REVISIONS = {'5M':'bdd20cfc15a3fea0e4cb5ccef37f8d3ca7aa335f',
             '28M':'49b26409ac87b5935539a5d8ffe7f397b720db47'}
CONTEXT = 2016


def vector(y):
    x = np.array(y, dtype=float, copy=True)
    if x.ndim != 1 or len(x) < 168 or np.isinf(x).any() or not np.isfinite(x).any():
        raise ValueError('Servono almeno 168 ore e valori finiti non negativi')
    if (x[np.isfinite(x)] < 0).any():
        raise ValueError('Il traffico non può essere negativo')
    return x


def fill_past(y):
    """Sequential seasonal fill; never looks at observations after a gap."""
    x = vector(y)
    seen = []
    for i in range(len(x)):
        if np.isfinite(x[i]):
            seen.append(x[i])
        elif i >= 168 and np.isfinite(x[i-168]):
            x[i] = x[i-168]
        elif seen:
            x[i] = seen[-1]
        else:
            x[i] = 0.
    return x


@lru_cache(maxsize=2)
def load_model(size):
    from timestral import TimestralForecaster
    root = Path(os.environ.get('HF_HOME', Path.home()/'.cache/huggingface'))
    path = root/f'hub/models--mistralai--Timestral-{size}/snapshots'/REVISIONS[size]
    if not path.is_dir():
        raise FileNotFoundError('Snapshot modello assente; usare scripts/download_models.py')
    return TimestralForecaster.from_pretrained(str(path), device='cpu')


def features(hours):
    h = np.asarray(hours)
    return np.column_stack([np.ones(len(h))] + [f(2*np.pi*k*h/p)
        for p, harmonics in [(24,3),(168,5)] for k in range(1,harmonics+1)
        for f in (np.sin,np.cos)])


def predict(history, model='weekly', horizon=24):
    if model not in MODELS or not isinstance(horizon,int) or not 1 <= horizon <= 168:
        raise ValueError('Modello o orizzonte non valido')
    raw = vector(history)[-CONTEXT:]
    x = fill_past(raw)
    if model in REVISIONS:
        result = load_model(model).forecast(x.copy(), prediction_length=horizon)
        out = {label:np.asarray(result.quantile(q)).reshape(-1) for label,q in
               [('p10',.1),('median',.5),('p90',.9)]}
    else:
        if model == 'last': p = np.full(horizon,x[-1])
        elif model == 'daily': p = np.resize(x[-24:],horizon)
        elif model == 'weekly': p = np.resize(x[-168:],horizon)
        elif model == 'weekly_mean':
            weeks = min(4,len(x)//168)
            p = np.resize(x[-weeks*168:].reshape(weeks,168).mean(axis=0),horizon)
        elif model == 'ets':
            from statsforecast.models import AutoETS
            p = AutoETS(season_length=24, model='AAA', damped=True).forecast(y=x,h=horizon)['mean']
        elif model == 'mstl':
            from statsforecast.models import MSTL, AutoETS
            p = MSTL(season_length=[24,168], trend_forecaster=AutoETS(model='ZZN')).forecast(y=x,h=horizon)['mean']
        else:
            # Calendar Fourier + causal 24/168h lags, fitted on training only.
            ix = np.arange(168,len(x))
            matrix = np.column_stack([features(ix)[:,1:], x[ix-24],x[ix-168]])
            mean, scale = matrix.mean(axis=0), matrix.std(axis=0)
            scale[scale<1e-12] = 1.
            design = np.column_stack([np.ones(len(ix)),(matrix-mean)/scale])
            penalty = np.eye(design.shape[1]); penalty[0,0] = 0.
            weights = np.linalg.solve(design.T@design+penalty,design.T@x[ix])
            all_values = list(x)
            output = []
            for t in range(len(x),len(x)+horizon):
                row = np.r_[features([t])[0,1:],all_values[t-24],all_values[t-168]]
                v = max(0,float(np.r_[1.,(row-mean)/scale]@weights))
                output.append(v); all_values.append(v)
            p = np.asarray(output)
        out = {'median': np.asarray(p)}
    if any(v.shape != (horizon,) or not np.isfinite(v).all() for v in out.values()):
        raise ValueError('Output previsione non valido')
    return {k:np.maximum(v,0) for k,v in out.items()}


def plan(prediction, throughput, margin=0., initial_units=None, startup_hours=1):
    """Day-ahead schedule. Startup lead holds previous capacity for the first hour."""
    p = np.asarray(prediction,dtype=float)
    if p.ndim != 1 or not len(p) or not np.isfinite(p).all() or (p<0).any():
        raise ValueError('Previsione non valida')
    if not np.isfinite([throughput,margin]).all() or throughput <= 0:
        raise ValueError('Capacità e margine non validi')
    if not isinstance(startup_hours,int) or not 0 <= startup_hours <= len(p):
        raise ValueError('Ritardo non valido')
    units = np.maximum(1,np.ceil((p+margin)/throughput)).astype(int)
    initial = int(units[0]) if initial_units is None else initial_units
    if not isinstance(initial,(int,np.integer)) or initial<1:
        raise ValueError('Capacità iniziale non valida')
    units[:startup_hours] = initial
    return units


def evaluate(actual, units, throughput):
    """Fluid hourly capacity proxy; no claim about packet latency or real SLA."""
    actual, units = np.asarray(actual,float),np.asarray(units,float)
    if actual.shape != units.shape or not np.isfinite(actual).all() or (actual<0).any():
        raise ValueError('Domanda non valida')
    if not np.isfinite(units).all() or (units<1).any() or throughput<=0:
        raise ValueError('Risorse non valide')
    capacity = units*throughput
    deficit = np.maximum(actual-capacity,0)
    return dict(unit_hours=float(units.sum()), deficit=float(deficit.sum()),
        demand=float(actual.sum()), deficit_fraction=float(deficit.sum()/actual.sum()) if actual.sum() else 0.,
        under_hours=int((deficit>0).sum()), idle=float(np.maximum(capacity-actual,0).sum()))


def demo(seed=42):
    rng = np.random.default_rng(seed)
    hours = pd.date_range('2026-01-05',periods=24*112,freq='h',tz='UTC')
    t = np.arange(len(hours))
    base = 900+650*np.maximum(np.sin((hours.hour.to_numpy()-7)*np.pi/12),0)
    y = base*np.where(hours.dayofweek.to_numpy()<5,1.,.65)*(1+.001*t/24)
    return pd.Series(np.maximum(0,y+rng.normal(0,70,len(t))),index=hours)
