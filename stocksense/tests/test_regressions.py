from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from stocksense import ingest
from stocksense.demo import synthetic_transactions
from stocksense.backtest import rolling_backtest
from stocksense.simulation import simulate


@pytest.mark.parametrize('kind', ['reversed', 'duplicate', 'gap', 'weekly'])
def test_evaluation_rejects_invalid_calendar(kind):
    index = pd.date_range('2024-01-01', periods=100)
    if kind == 'reversed':
        index = index[::-1]
    elif kind == 'duplicate':
        index = index[:50].append(index[49:99])
    elif kind == 'gap':
        index = index.delete(50)
    else:
        index = pd.date_range('2024-01-01', periods=100, freq='7D')
    daily = pd.DataFrame({'A': np.ones(len(index))}, index=index)
    with pytest.raises(ValueError, match='calendar'):
        rolling_backtest(daily, ['moving_average'], folds=1)
    with pytest.raises(ValueError, match='calendar'):
        simulate(daily, 60, ['moving_average'])


def test_dashboard_refreshes_changed_excel_without_clearing_cache(tmp_path, monkeypatch):
    raw, cached = tmp_path/'retail.xlsx', tmp_path/'retail.parquet'
    frame = synthetic_transactions(days=400, products=1)
    frame.to_excel(raw, index=False)
    fingerprint = ingest.source_fingerprint
    convert = ingest.converti_una_volta
    monkeypatch.setattr(ingest, 'source_fingerprint', lambda path=raw: fingerprint(path))
    monkeypatch.setattr(ingest, 'converti_una_volta', lambda: convert(raw, cached))
    app = AppTest.from_file(Path(__file__).resolve().parents[1]/'app/streamlit_app.py').run(timeout=30)
    app.sidebar.selectbox[0].set_value('uci').run(timeout=30)
    assert not app.exception
    first = frame.InvoiceDate.max()+pd.Timedelta(days=1)
    assert any(str(first.date()) in c.value for c in app.caption)
    frame.InvoiceDate += pd.Timedelta(days=30)
    frame.to_excel(raw, index=False)
    app.run(timeout=30)
    assert not app.exception
    second = frame.InvoiceDate.max()+pd.Timedelta(days=1)
    assert any(str(second.date()) in c.value for c in app.caption)
