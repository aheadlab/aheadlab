"""Lazy, CPU-only Timestral boundary. Errors never select a fallback model."""
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

MAX_CONTEXT = 32768
SIZES = ("5M", "28M", "123M", "209M")


@dataclass
class Previsione:
    mediana: np.ndarray
    p10: np.ndarray
    p90: np.ndarray
    p01: np.ndarray
    p99: np.ndarray

    def __post_init__(self):
        for name in ("mediana", "p10", "p90", "p01", "p99"):
            value = np.array(getattr(self, name), dtype=float, copy=True)
            if value.ndim != 1 or not value.size or not np.isfinite(value).all():
                raise ValueError(f"{name} must be a nonempty finite 1D array")
            if value.shape != np.shape(self.mediana):
                raise ValueError("Quantile shapes must match")
            setattr(self, name, value)
        ordered = np.stack([self.p01, self.p10, self.mediana, self.p90, self.p99])
        if np.any(ordered[:-1] > ordered[1:]):
            raise ValueError("Quantiles must be ordered")


def _history(history):
    history = np.asarray(history, dtype=float)
    if history.ndim != 1 or not history.size or np.isinf(history).any():
        raise ValueError("History must be nonempty 1D, without infinity")
    history = history[-MAX_CONTEXT:]
    if not np.isfinite(history).any():
        raise ValueError("Retained history must contain an observation")
    return history.copy()


@lru_cache(maxsize=4)
def carica_modello(taglia="5M"):
    if taglia not in SIZES:
        raise ValueError(f"Model size must be one of {SIZES}")
    from timestral import TimestralForecaster
    return TimestralForecaster.from_pretrained(f"mistralai/Timestral-{taglia}", device="cpu")


def _vector(value, horizon):
    if hasattr(value, "detach"):
        value = value.detach().cpu().numpy()
    value = np.asarray(value, dtype=float)
    if value.shape != (1, 1, horizon):
        raise ValueError(f"Expected Timestral shape (1, 1, {horizon}), got {value.shape}")
    return value[0, 0, :]


def _forecast(history, horizon, size, **kwargs):
    if size not in SIZES:
        raise ValueError(f"Model size must be one of {SIZES}")
    result = carica_modello(size).forecast(history, prediction_length=horizon, **kwargs)
    return Previsione(
        _vector(result.median, horizon),
        _vector(result.quantile(0.10), horizon),
        _vector(result.quantile(0.90), horizon),
        _vector(result.quantile(0.01), horizon),
        _vector(result.quantile(0.99), horizon),
    )


def prevedi(storico, orizzonte, taglia="5M"):
    """Forecast one series, preserving missing observations as NaN."""
    if (isinstance(orizzonte, (bool, np.bool_))
            or not isinstance(orizzonte, (int, np.integer)) or orizzonte < 1):
        raise ValueError("orizzonte must be a positive integer")
    return _forecast(_history(storico), int(orizzonte), taglia)


def prevedi_con_covariate(storico, covariate_storiche, covariate_future, taglia="5M"):
    """Accept aligned (T,C) past and finite (H,C) future covariates."""
    original = np.asarray(storico, dtype=float)
    history = _history(original)
    past = np.asarray(covariate_storiche, dtype=float)
    future = np.asarray(covariate_future, dtype=float)
    if (past.ndim != 2 or future.ndim != 2 or past.shape[0] != original.size
            or past.shape[1] == 0 or past.shape[1] != future.shape[1] or future.shape[0] == 0):
        raise ValueError("Covariates must have aligned shapes (T,C) and (H,C), C,H > 0")
    if np.isinf(past).any() or not np.isfinite(future).all():
        raise ValueError("Past covariates cannot contain infinity; future must be finite")
    past = past[-MAX_CONTEXT:]
    if not np.isfinite(past).any(axis=0).all():
        raise ValueError("Each retained historical covariate needs an observation")
    known = np.concatenate([past, future], axis=0).T[None, :, :]
    return _forecast(history, future.shape[0], taglia, known_covariates=known)
