import numpy as np
import pytest

from solarcast.baselines import moving_average, seasonal_naive
from solarcast.metrics import coverage, mae, mase


def test_metrics():
    assert mae([1, 3], [2, 1]) == 1.5
    assert mase([1, 3], [2, 1], [0, 2, 4]) == .75
    assert mase([1], [2], [1, 2, 4, 6], m=2) == pytest.approx(1 / 3.5)
    assert np.isnan(mase([1], [2], [1, 1, 1]))
    assert coverage([1, 2, 3], [1, 0, 4], [1, 2, 5]) == 2 / 3


@pytest.mark.parametrize("bad", [[], [[1]], [np.nan], [np.inf]])
def test_bad_vectors(bad):
    for fn in (lambda: mae(bad, [1]), lambda: coverage([1], bad, [2]),
               lambda: mase([1], [2], bad)):
        with pytest.raises(ValueError):
            fn()


def test_shapes_and_bounds():
    with pytest.raises(ValueError):
        mae([1, 2], [1])
    with pytest.raises(ValueError):
        coverage([1], [2], [0])
    with pytest.raises(ValueError):
        coverage([1, 2], [0], [3])


@pytest.mark.parametrize("m", [0, -1, 3, True, 1.5])
def test_bad_season(m):
    with pytest.raises(ValueError):
        mase([1], [2], [1, 2, 3], m)


def test_baselines():
    np.testing.assert_array_equal(seasonal_naive([1, 2, 3], 5, period=2), [2, 3, 2, 3, 2])
    np.testing.assert_array_equal(moving_average([1, 2, 4], 2, window=2), [3, 3])
    np.testing.assert_array_equal(moving_average([2], 1), [2])
    with pytest.raises(ValueError):
        seasonal_naive([1], 2)
    for baseline in (seasonal_naive, moving_average):
        with pytest.raises(ValueError):
            baseline([np.nan], 1)
        with pytest.raises(ValueError):
            baseline(np.arange(30), 0)
        with pytest.raises(ValueError):
            baseline(np.arange(30), True)
