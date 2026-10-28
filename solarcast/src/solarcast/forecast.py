"""Domain API: normalized production; no manufactured baseline uncertainty."""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from . import forecaster
from .prepare import validate_index

COVARIATES = ['shortwave_radiation', 'cloud_cover', 'temperature_2m']
METHODS = ('seasonal_naive24', 'radiation_regression', 'A', 'B')


@dataclass
class Forecast:
    frame: pd.DataFrame
    metadata: dict


def forecast(history, future_weather, method='seasonal_naive24', model='5M', max_context=8760,
             operational=False, now=None):
    validate_index(history.index)
    validate_index(future_weather.index)
    if future_weather.index[0] != history.index[-1] + pd.Timedelta(hours=1):
        raise ValueError('Future must immediately follow target history')
    if method not in METHODS or not isinstance(max_context, int) or not 24 <= max_context <= forecaster.MAX_CONTEXT:
        raise ValueError('Invalid method or context (24..32768)')
    if model not in forecaster.SIZES:
        raise ValueError('Invalid model size')
    if operational:
        now = pd.Timestamp.now(tz='UTC') if now is None else pd.Timestamp(now)
        if now.tzinfo is None or not pd.Timedelta(0) <= now-history.index[-1] <= pd.Timedelta(hours=2):
            raise ValueError('Operational forecasting requires recent measured target')
    train = history.iloc[-max_context:]
    y = train.kwh.to_numpy(dtype=float)
    if len(y) < 24 or np.isinf(y).any() or not np.isfinite(y).any() or np.nanmin(y) < 0:
        raise ValueError('Invalid normalized target history')
    h = len(future_weather)
    if method == 'seasonal_naive24':
        median = np.resize(y[-24:], h)
        output = {'median': median}
    elif method == 'radiation_regression':
        fit = train.iloc[-720:]
        x = fit.shortwave_radiation.to_numpy(dtype=float)
        yy = fit.kwh.to_numpy(dtype=float)
        valid = np.isfinite(x) & np.isfinite(yy)
        future = future_weather.shortwave_radiation.to_numpy(dtype=float)
        if valid.sum() < 24 or not np.isfinite(future).all():
            raise ValueError('Regression requires finite radiation and 24 training pairs')
        a, b = np.linalg.lstsq(np.column_stack([x[valid], np.ones(valid.sum())]), yy[valid], rcond=None)[0]
        output = {'median': a*future+b}
    else:
        if method == 'A':
            p = forecaster.prevedi(y, h, model)
        else:
            p = forecaster.prevedi_con_covariate(y, train[COVARIATES].to_numpy(),
                                                future_weather[COVARIATES].to_numpy(), model)
        output = dict(median=p.mediana, p10=p.p10, p90=p.p90)
    result = pd.DataFrame(output, index=future_weather.index).clip(lower=0)
    return Forecast(result, dict(method=method, model=model if method in ('A', 'B') else 'baseline',
        max_context=max_context, context_used=len(train), unit='kWh/kWp',
        weather='forecast' if operational else ('observed_oracle' if method in ('B', 'radiation_regression') else 'unused'),
        mode='operational_user_target' if operational else 'retrospective'))
