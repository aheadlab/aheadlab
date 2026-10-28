"""Strict metrics for equally aligned finite vectors."""
import numpy as np


def _vector(value):
    value = np.asarray(value, dtype=float)
    if value.ndim != 1 or not value.size or not np.isfinite(value).all():
        raise ValueError("Expected a nonempty finite 1D vector")
    return value


def _aligned(*values):
    arrays = tuple(_vector(value) for value in values)
    if any(array.shape != arrays[0].shape for array in arrays):
        raise ValueError("Vector shapes must match")
    return arrays


def mae(reale, previsto):
    real, predicted = _aligned(reale, previsto)
    return float(np.mean(np.abs(real - predicted)))


def mase(reale, previsto, storico, m=1):
    error = mae(reale, previsto)
    history = _vector(storico)
    if (isinstance(m, (bool, np.bool_)) or not isinstance(m, (int, np.integer))
            or not 0 < m < len(history)):
        raise ValueError("m must be a positive integer smaller than history length")
    scale = float(np.mean(np.abs(history[m:] - history[:-m])))
    return error / scale if scale else float("nan")


def coverage(reale, basso, alto):
    real, lower, upper = _aligned(reale, basso, alto)
    if np.any(lower > upper):
        raise ValueError("Lower bounds must not exceed upper bounds")
    return float(np.mean((real >= lower) & (real <= upper)))


copertura = coverage
