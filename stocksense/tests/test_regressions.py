from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from stocksense import api
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


def test_api_refreshes_changed_excel_without_clearing_cache(tmp_path, monkeypatch):
    raw, cached = tmp_path/'retail.xlsx', tmp_path/'retail.parquet'
    frame = synthetic_transactions(days=400, products=1)
    frame.to_excel(raw, index=False)
    fingerprint = ingest.source_fingerprint
    convert = ingest.converti_una_volta
    monkeypatch.setattr(api, 'source_fingerprint', lambda path: fingerprint(raw))
    monkeypatch.setattr(api, 'converti_una_volta', lambda *args: convert(raw, cached))
    api.dataset.cache_clear()
    client = TestClient(api.app)
    response = client.post('/api/forecast', json={'source': 'uci'})
    assert response.status_code == 200
    first = frame.InvoiceDate.max()+pd.Timedelta(days=1)
    assert pd.Timestamp(response.json()['as_of']) == first
    frame.InvoiceDate += pd.Timedelta(days=30)
    frame.to_excel(raw, index=False)
    response = client.post('/api/forecast', json={'source': 'uci'})
    assert response.status_code == 200
    second = frame.InvoiceDate.max()+pd.Timedelta(days=1)
    assert pd.Timestamp(response.json()['as_of']) == second
    api.dataset.cache_clear()
