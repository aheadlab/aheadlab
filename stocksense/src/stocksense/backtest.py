"""Expanding rolling origins; raw evaluation targets and weekly MASE scale."""
import numpy as np
import pandas as pd
from .forecast_all import forecast
from .metrics import mase, mae
from .baselines import _integer
from .prepare import validate_daily


def origins(length, folds=8, horizon=30, step=30):
    folds, horizon, step = (_integer(v, n) for v, n in
                            [(folds, 'folds'), (horizon, 'horizon'), (step, 'step')])
    first = length-horizon-(folds-1)*step
    if first < 28:
        raise ValueError('Insufficient training history')
    return list(range(first, first+folds*step, step))


def rolling_backtest(daily, models, folds=8, horizon=30, step=30, predictor=forecast):
    validate_daily(daily)
    rows = []
    for fold, cutoff in enumerate(origins(len(daily), folds, horizon, step)):
        for sku in daily:
            history = daily[sku].iloc[:cutoff].to_numpy()
            target = daily[sku].iloc[cutoff:cutoff+horizon].to_numpy()
            for model in models:
                prediction = predictor(history, horizon, model).mediana
                rows.append(dict(fold=fold, cutoff=daily.index[cutoff], sku=sku, modello=model,
                                 mase=mase(target, prediction, history, m=7), mae=mae(target, prediction)))
    scores = pd.DataFrame(rows)
    minimum = scores.groupby(['fold', 'sku']).mase.transform('min')
    scores['vittoria'] = scores.mase.eq(minimum) & scores.mase.notna()
    def geometric(values):
        values = values.dropna().to_numpy()
        return (0. if (values == 0).any() else float(np.exp(np.log(values).mean()))) if len(values) else np.nan
    summary = scores.groupby('modello', as_index=False).agg(
        mase_geometrico=('mase', geometric), vittorie=('vittoria', 'sum'),
        casi_validi=('mase', 'count'), mae_media=('mae', 'mean'))
    return scores, summary
