import os
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from cloudguard import forecaster as f


def output(h):
    return SimpleNamespace(median=np.full((1, 1, h), .5),
                           quantile=lambda q: np.full((1, 1, h), q))


@pytest.fixture
def model(monkeypatch):
    model = Mock()
    model.forecast.side_effect = lambda context, prediction_length, **kw: output(prediction_length)
    monkeypatch.setattr(f, "carica_modello", lambda size: model)
    return model


def test_readonly_history_is_copied(model):
    history = np.arange(40., dtype=float)
    history.flags.writeable = False
    f.prevedi(history, 1)
    actual = model.forecast.call_args.args[0]
    assert actual.flags.writeable
    assert not np.shares_memory(actual, history)


@pytest.mark.parametrize("h", [1, 14, 1025])
def test_shapes_and_nan(model, h):
    result = f.prevedi([1, np.nan, 2], h)
    assert result.mediana.shape == (h,)
    assert np.all(result.p01 <= result.p10)
    assert np.all(result.p10 <= result.mediana)
    assert np.all(result.mediana <= result.p90)
    assert np.all(result.p90 <= result.p99)
    assert np.isnan(model.forecast.call_args.args[0][1])


@pytest.mark.parametrize("history", [[], [[1]], [np.nan], [np.inf], [1, -np.inf]])
def test_invalid_history(model, history):
    with pytest.raises(ValueError):
        f.prevedi(history, 1)
    model.forecast.assert_not_called()


@pytest.mark.parametrize("h", [0, -1, True, 1.5])
def test_invalid_horizon(model, h):
    with pytest.raises(ValueError):
        f.prevedi([1], h)


def test_truncation_and_covariate_alignment(model):
    history = np.arange(33000.)
    past = np.column_stack([history, history + 1])
    future = np.array([[40000., 40001.]])
    result = f.prevedi_con_covariate(history, past, future)
    args = model.forecast.call_args
    np.testing.assert_array_equal(args.args[0], history[-32768:])
    known = args.kwargs["known_covariates"]
    assert known.shape == (1, 2, 32769)
    np.testing.assert_array_equal(known[0, :, :-1].T, past[-32768:])
    np.testing.assert_array_equal(known[0, :, -1], future[0])
    assert result.mediana.shape == (1,)


@pytest.mark.parametrize("past,future", [
    ([[1]], [[1]]), ([1, 2], [[1]]), ([[1], [2]], []),
    ([[1], [2]], [[1, 2]]), ([[1], [2]], [[np.nan]]),
    ([[np.inf], [2]], [[1]]), ([[np.nan], [np.nan]], [[1]]),
])
def test_invalid_covariates(model, past, future):
    with pytest.raises(ValueError):
        f.prevedi_con_covariate([1, 2], past, future)
    model.forecast.assert_not_called()


def test_retained_history_must_have_observations(model):
    with pytest.raises(ValueError):
        f.prevedi(np.r_[1, np.full(32768, np.nan)], 1)


@pytest.mark.parametrize("bad", [0.5, [[.5]], [np.nan], [np.inf], [.5, .5]])
def test_dataclass_rejects_bad_arrays(bad):
    with pytest.raises(ValueError):
        f.Previsione([.5], bad, [.9], [.01], [.99])


def test_crossed_quantiles():
    with pytest.raises(ValueError):
        f.Previsione([.5], [.6], [.9], [.01], [.99])


def test_no_fallback(model):
    model.forecast.side_effect = RuntimeError("model failed")
    with pytest.raises(RuntimeError, match="model failed"):
        f.prevedi([1], 1)


def test_unexpected_output_shape(model):
    model.forecast.side_effect = None
    model.forecast.return_value = SimpleNamespace(median=np.ones(1))
    with pytest.raises(ValueError, match="Timestral shape"):
        f.prevedi([1], 1)


def test_tensor_conversion():
    tensor = Mock()
    tensor.detach.return_value.cpu.return_value.numpy.return_value = np.ones((1, 1, 1))
    np.testing.assert_array_equal(f._vector(tensor, 1), [1])


def test_lazy_cached_loader(monkeypatch):
    loader = Mock(return_value=object())
    monkeypatch.setitem(sys.modules, "timestral", SimpleNamespace(
        TimestralForecaster=SimpleNamespace(from_pretrained=loader)))
    f.carica_modello.cache_clear()
    try:
        assert f.carica_modello() is f.carica_modello()
        loader.assert_called_once_with("mistralai/Timestral-5M", device="cpu")
        with pytest.raises(ValueError):
            f.carica_modello("invalid")
    finally:
        f.carica_modello.cache_clear()


@pytest.mark.integration
@pytest.mark.skipif(os.getenv("RUN_MODEL_TESTS") != "1", reason="Set RUN_MODEL_TESTS=1 for real CPU model")
@pytest.mark.parametrize("h", [1, 14])
def test_real_model(h):
    history = 10 + np.sin(np.arange(128) * 2 * np.pi / 7)
    assert f.prevedi(history, h).mediana.shape == (h,)
    past = np.arange(128.)[:, None]
    future = np.arange(128., 128 + h)[:, None]
    assert f.prevedi_con_covariate(history, past, future).mediana.shape == (h,)
