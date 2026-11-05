import json
from fastapi.testclient import TestClient
from cloudguard import api
from cloudguard.api_support import calculation

client = TestClient(api.app)


def test_health_and_meta():
    assert client.get('/api/health').json() == {'status': 'ok', 'app': 'cloudguard'}
    assert 'Amazon EC2' in client.get('/api/meta').json()['services']


def test_forecast_baseline_and_contract():
    r = client.post('/api/forecast', json={})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data['source'] == 'synthetic'
    assert len(data['forecast']) == 30 and len(data['history']) == 90
    assert 'lower' not in data['forecast'][0]
    assert data['month']['basso'] is None
    assert data['metadata']['sends_enabled'] is False
    json.loads(r.text, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def test_invalid_and_busy():
    assert client.post('/api/forecast', json={'horizon': 0}).status_code == 422
    assert client.post('/api/forecast', json={'service': 'invalid'}).status_code == 422
    assert client.post('/api/forecast', json={'send': True}).status_code == 422
    with calculation():
        assert client.post('/api/forecast', json={}).status_code == 409


def test_model_error_sanitized(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError('secret-token')
    monkeypatch.setattr(api, 'forecast', fail)
    r = client.post('/api/forecast', json={'model': '5M'})
    assert r.status_code == 503 and 'secret-token' not in r.text


def test_reports_and_routes():
    reports = client.get('/api/reports').json()['reports']
    assert reports
    assert client.get('/api/reports/'+reports[0]['id']).status_code == 200
    assert client.get('/api/reports/not-allowed').status_code == 404
    assert client.get('/api/not-found').status_code == 404
