import pytest
from fastapi.testclient import TestClient
from solarcast import api
from solarcast.api_support import calculation

client = TestClient(api.app)


def test_health_meta():
    assert client.get('/api/health').json()['app'] == 'solarcast'
    assert client.get('/api/meta').status_code == 200


def test_scale_and_oracle():
    one = client.post('/api/forecast', json={'kwp': 1, 'method': 'radiation_regression'}).json()
    six = client.post('/api/forecast', json={'kwp': 6, 'method': 'radiation_regression'}).json()
    assert len(six['forecast']) == 48
    assert six['metrics']['energy'] == pytest.approx(one['metrics']['energy']*6)
    assert six['metadata']['weather'] == 'observed_oracle'
    assert six['metadata']['retrospective'] is True
    assert 'lower' not in six['forecast'][0]
    assert len(six['days']) == 2


def test_validation_and_busy():
    assert client.post('/api/forecast', json={'method': 'B'}).status_code == 422
    assert client.post('/api/forecast', json={'kwp': -1}).status_code == 422
    assert client.post('/api/forecast', json={'origin': '2030-01-01'}).status_code == 422
    with calculation():
        assert client.post('/api/forecast', json={}).status_code == 409


def test_upstream_failure(monkeypatch):
    def fail(*a, **kw):
        raise OSError('private-path')
    monkeypatch.setattr(api, 'dataset', fail)
    r = client.post('/api/forecast', json={'source': 'pvgis'})
    assert r.status_code == 503 and 'private-path' not in r.text


def test_report_whitelist():
    reports = client.get('/api/reports').json()['reports']
    assert reports
    assert client.get('/api/reports/'+reports[0]['id']).status_code == 200
    assert client.get('/api/reports/not-allowed').status_code == 404
    assert client.get('/api/not-found').status_code == 404
