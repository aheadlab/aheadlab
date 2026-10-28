import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from solarcast.demo import synthetic
from solarcast.prepare import unisci, validate_index
from solarcast.forecast import forecast
from solarcast.logic import fasce_migliori
from solarcast.backtest import run_backtest, save_results
from solarcast import ingest
from solarcast.notify import telegram


def test_utc_duplicates_missing():
    idx = pd.date_range('2023-01-01', periods=3, freq='h', tz='UTC')
    for bad in [idx.tz_localize(None), idx[[0,0]], idx[::-1], idx+pd.Timedelta(minutes=10)]:
        with pytest.raises(ValueError):
            validate_index(bad)
    pv = pd.DataFrame({'kwh':[1., 3.]}, index=idx[[0,2]])
    weather = pd.DataFrame({'cloud_cover':[0,0,0]}, index=idx)
    assert np.isnan(unisci(pv, weather).kwh.iloc[1])


@pytest.mark.parametrize('start', ['2023-03-26 00:00', '2023-10-29 00:00'])
def test_blocks_dst_scale_last_minimum(start):
    idx = pd.date_range(start, periods=4, freq='h', tz='UTC')
    blocks = fasce_migliori([.5]*4, [.4]*4, idx, 6)
    assert len(blocks) == 1
    b = blocks[0]
    assert b['expected_kwh'] == 12
    assert b['end']-b['start'] == pd.Timedelta(hours=4)
    assert b['end'].tz_convert('UTC') == idx[-1]+pd.Timedelta(hours=1)
    assert fasce_migliori([0,0,0,1], None, idx, 6) == []
    assert fasce_migliori([1]*4, None, idx, 6)[0]['basis'] == 'median_indicative'


def test_forecast_validation_and_training_only():
    data = synthetic()
    history, future = data.iloc[:1000], data.iloc[1000:1048].copy()
    first = forecast(history, future, 'radiation_regression')
    future['kwh'] = 1e9
    second = forecast(history, future, 'radiation_regression')
    pd.testing.assert_frame_equal(first.frame, second.frame)
    assert first.metadata['weather'] == 'observed_oracle'
    assert list(first.frame) == ['median']
    with pytest.raises(ValueError):
        forecast(history, future.iloc[1:])
    with pytest.raises(ValueError):
        forecast(history, future, operational=True, now='2026-01-01T00:00Z')
    forecast(history, future, operational=True, now=history.index[-1]+pd.Timedelta(hours=1))
    with pytest.raises(ValueError):
        forecast(history, future, max_context=0)


def test_covariate_contract(monkeypatch):
    from solarcast import forecaster
    data = synthetic().iloc[:200]
    def fake(y, past, future, size):
        assert y.shape == (100,)
        assert past.shape == (100,3)
        assert future.shape == (48,3)
        return forecaster.Previsione(*[np.zeros(48) for _ in range(5)])
    monkeypatch.setattr(forecaster, 'prevedi_con_covariate', fake)
    out = forecast(data.iloc[:152], data.iloc[152:], 'B', max_context=100)
    assert out.metadata['context_used'] == 100
    assert 'p10' in out.frame


def test_ingest_cache_params_timeout(monkeypatch, tmp_path):
    calls = []
    class Response:
        def raise_for_status(self): pass
        def json(self):
            return {'outputs':{'hourly':[{'time':'20230101:0010','P':1000}, {'time':'20230101:0110','P':None}]}}
    def get(url, params, timeout):
        calls.append((url, params, timeout))
        return Response()
    monkeypatch.setattr(ingest.requests, 'get', get)
    result = ingest.scarica_pvgis(45.82, 8.83, 2023, 2023, cache_dir=tmp_path)
    assert result.kwh.iloc[0] == 1 and pd.isna(result.kwh.iloc[1])
    assert str(result.index.tz) == 'UTC'
    ingest.scarica_pvgis(45.82, 8.83, 2023, 2023, cache_dir=tmp_path)
    assert len(calls) == 1
    assert calls[0][1]['peakpower'] == 1 and calls[0][2] == 120
    ingest.scarica_pvgis(45.82, 8.83, 2023, 2023, angle=40, cache_dir=tmp_path)
    assert len(calls) == 2
    assert 'v5_3/seriescalc' in calls[0][0]
    for field in ['lat','lon','angle','aspect','loss','startyear','endyear']:
        p = calls[0][1].copy(); p[field] += 1
        assert ingest.cache_path(calls[0][0], p) != ingest.cache_path(calls[0][0], calls[0][1])


def test_weather_and_http_error(monkeypatch, tmp_path):
    calls = []
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'hourly': {'time':['2023-01-01T00:00'], 'shortwave_radiation':[None]}}
    def get(url, params, timeout):
        calls.append((url, params, timeout)); return Response()
    monkeypatch.setattr(ingest.requests, 'get', get)
    weather = ingest.scarica_meteo_storico(1,2,'2023-01-01','2023-12-31', tmp_path)
    assert pd.isna(weather.iloc[0,0])
    ingest.scarica_meteo_previsto(1,2,cache_dir=tmp_path)
    assert [c[2] for c in calls] == [120,60]
    assert all(c[1]['timezone']=='UTC' and 'cloud_cover' in c[1]['hourly'] for c in calls)
    def fail(*a, **kw): raise ingest.requests.HTTPError('bad')
    monkeypatch.setattr(ingest.requests, 'get', fail)
    with pytest.raises(ingest.requests.HTTPError):
        ingest.scarica_pvgis(1,2,2023,2023,cache_dir=tmp_path)


def test_backtest_and_dry_run(tmp_path, monkeypatch):
    daily, summary, meta = run_backtest(synthetic(), quick=True)
    assert meta['origins'] == 4 and meta['max_context'] == 720
    assert daily.season.nunique() == 4
    assert daily.coverage.isna().all()
    assert set(daily.weather) == {'unused','observed_oracle'}
    save_results(daily, summary, meta, tmp_path)
    assert json.loads((tmp_path/'metadata.json').read_text())['quick']
    monkeypatch.setattr('requests.post', lambda *a, **kw: pytest.fail('Network forbidden'))
    assert telegram('demo')['dry_run']


def test_app():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / 'app/streamlit_app.py').run(timeout=30)
    assert not app.exception
    app.sidebar.radio[0].set_value('Risultati').run()
    assert not app.exception
