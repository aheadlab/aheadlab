import numpy as np
import pandas as pd
import pytest
from stocksense.forecast_all import PointForecast, forecast
from stocksense.logic import calcola_riordino
from stocksense.forecaster import Previsione
from stocksense.prepare import pulisci, vendite_giornaliere, winsorize_training
from stocksense.simulation import simulate
from stocksense.backtest import rolling_backtest, origins
from stocksense.ingest import converti_una_volta


def test_reorder_minimum_not_multiple_and_pending():
    pred = PointForecast(np.full(21, 1.))
    assert calcola_riordino(pred, 10, lotto_minimo=6)['da_ordinare'] == 11
    assert calcola_riordino(pred, 20, lotto_minimo=6)['da_ordinare'] == 6
    result = calcola_riordino(pred, 10, 11)
    assert result['da_ordinare'] == result['scorta_sicurezza'] == 0
    assert 'puntuale' in result['politica']


@pytest.mark.parametrize('kwargs', [{'giacenza': -1}, {'in_arrivo': -1}, {'in_arrivo': np.nan},
    {'lead_time': 0}, {'ciclo': 1.5}, {'lotto_minimo': 0}, {'lead_time': True}])
def test_invalid_policy(kwargs):
    with pytest.raises(ValueError):
        calcola_riordino(PointForecast(np.ones(21)), **dict({'giacenza': 0}, **kwargs))


def test_horizon_clipping_and_quantiles():
    with pytest.raises(ValueError):
        calcola_riordino(PointForecast(np.ones(20)), 0)
    assert calcola_riordino(PointForecast(-np.ones(21)), 0)['da_ordinare'] == 0
    p = Previsione(np.ones(21), np.zeros(21), np.full(21, 2), np.zeros(21), np.full(21, 3))
    assert calcola_riordino(p, 0)['scorta_sicurezza'] == 21


def transactions():
    return pd.DataFrame({'Invoice': ['1', '2', 'C3', '4', '5', '6'],
      'StockCode': ['A', 'B', 'A', 'POST', 'A', 'A'], 'Quantity': [10, 1000, 3, 1, -1, 1],
      'Price': [1]*6, 'InvoiceDate': ['2020-01-01', '2020-01-03', '2020-01-01',
                                        '2020-01-01', '2020-01-01', '2020-01-03']})


def test_clean_selection_calendar():
    clean = pulisci(transactions())
    assert len(clean) == 3
    daily = vendite_giornaliere(clean, 1, '2020-01-03')
    assert list(daily) == ['A']
    assert daily.A.tolist() == [10, 0, 1]
    x = np.r_[np.ones(200), 1000.]
    before = x.copy()
    assert winsorize_training(x)[-1] == 1
    np.testing.assert_array_equal(x, before)


def test_delayed_arrivals_lost_sales_no_leakage():
    daily = pd.DataFrame({'A': np.ones(35)}, index=pd.date_range('2020-01-01', periods=35))
    seen = []
    def predict(history, h, model):
        seen.append(len(history))
        return PointForecast(np.ones(h))
    config = {'*': dict(lead_time=2, ciclo=7, lotto_minimo=1, livello='p90')}
    ledger, summary = simulate(daily, 28, ['test'], config, {'A': 0}, predict)
    assert seen == [28]
    assert ledger.arrivi.tolist() == [0, 0, 9, 0, 0, 0, 0]
    assert ledger.vendite_perse.sum() == 2
    assert ledger.giacenza.iloc[-1] == 4  # lost sales never subtracted later
    assert ledger.in_arrivo.iloc[0] == 9
    assert summary.giorni_stockout.iloc[0] == 2
    changed = daily.copy(); changed.iloc[30:] = 10000
    other, _ = simulate(changed, 28, ['test'], config, {'A': 0}, predict)
    pd.testing.assert_frame_equal(ledger.iloc[:2], other.iloc[:2])


def test_rolling_uses_raw_target_and_training_scale():
    daily = pd.DataFrame({'A': np.arange(100.)}, index=pd.date_range('2020-01-01', periods=100))
    seen = []
    def predictor(history, h, model):
        seen.append(history.copy())
        return PointForecast(np.zeros(h))
    scores, summary = rolling_backtest(daily, ['test'], 2, 10, 10, predictor)
    assert [len(x) for x in seen] == [80, 90]
    assert scores.mae.iloc[0] == 84.5
    assert scores.mase.iloc[0] == pytest.approx(84.5/7)
    assert summary.vittorie.iloc[0] == 2
    assert origins(730)[0] == 490


def test_all_sheets_cache_invalidates(tmp_path):
    raw, out = tmp_path/'retail.xlsx', tmp_path/'cache.parquet'
    with pd.ExcelWriter(raw) as writer:
        transactions().iloc[:1].to_excel(writer, sheet_name='year1', index=False)
        transactions().iloc[1:2].to_excel(writer, sheet_name='year2', index=False)
    assert len(converti_una_volta(raw, out)) == 2
    assert len(converti_una_volta(raw, out)) == 2
    transactions().to_excel(raw, index=False)
    assert len(converti_una_volta(raw, out)) == 6


def test_baseline_has_no_quantiles():
    pred = forecast(np.arange(40.), 30, 'moving_average')
    assert not hasattr(pred, 'p90')


@pytest.mark.parametrize('stock', [-1, np.nan, np.inf])
def test_invalid_initial_inventory(stock):
    daily = pd.DataFrame({'A': np.ones(40)})
    with pytest.raises(ValueError):
        simulate(daily, 28, ['moving_average'], initial_stock={'A': stock})


def test_pending_stock_prevents_duplicate_order_and_models_share_start():
    daily = pd.DataFrame({'A': np.ones(56)})
    def predictor(history, h, model):
        return PointForecast(np.ones(h))
    ledger, _ = simulate(daily, 28, ['a', 'b'], initial_stock={'A': 0}, predictor=predictor)
    a = ledger[ledger.modello == 'a'].reset_index(drop=True)
    b = ledger[ledger.modello == 'b'].reset_index(drop=True)
    assert a.ordine.iloc[0] == 21
    assert a.ordine.iloc[7] == 0
    pd.testing.assert_frame_equal(a.drop(columns='modello'), b.drop(columns='modello'))
