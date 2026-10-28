"""Domain adapter: point baselines stay point forecasts, all outputs >= 0."""
from dataclasses import dataclass
import numpy as np
from . import baselines
from .forecaster import Previsione, prevedi
from .prepare import winsorize_training

BASELINES = ('seasonal_naive', 'moving_average', 'auto_ets')
MODELS = BASELINES + ('5M', '28M', '209M')


@dataclass
class PointForecast:
    mediana: np.ndarray


def forecast(history, h=30, model='seasonal_naive'):
    history = winsorize_training(history)
    if model in BASELINES:
        return PointForecast(np.maximum(getattr(baselines, model)(history, h), 0))
    if model not in MODELS:
        raise ValueError(f'Unknown model: {model}')
    prediction = prevedi(history, h, taglia=model)
    return Previsione(**{key: np.maximum(getattr(prediction, key), 0)
                        for key in ('mediana', 'p10', 'p90', 'p01', 'p99')})


def prevedi_tutti(vendite, orizzonte=30, taglia='28M'):
    return {sku: forecast(vendite[sku].values, orizzonte, taglia) for sku in vendite}
