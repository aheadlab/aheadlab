"""Deterministic comparisons without implicit missing-value imputation."""
import numpy as np

from .metrics import _vector


def _integer(value, name):
    if (isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer))
            or value < 1):
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def seasonal_naive(history, h, period=7):
    history = _vector(history)
    h, period = _integer(h, "h"), _integer(period, "period")
    if len(history) < period:
        raise ValueError("History must include at least one complete season")
    return np.resize(history[-period:], h)


def moving_average(history, h, window=28):
    """Use up to window trailing observations, including short histories."""
    history = _vector(history)
    h, window = _integer(h, "h"), _integer(window, "window")
    return np.full(h, history[-window:].mean())
