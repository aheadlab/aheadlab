from fastapi.testclient import TestClient
from stocksense import api
from stocksense.api_support import calculation

client = TestClient(api.app)


def test_health_meta():
    assert client.get('/api/health').json()['app'] == 'stocksense'
    assert client.get('/api/meta').status_code == 200


def test_orders_and_products():
    r = client.post('/api/forecast', json={'top_n': 2})
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data['orders']) == len(data['products']) == 2
    assert data['metadata']['orders_sent'] is False
    assert 'SIMULATO' in data['metadata']['inventory']
    assert all('lower' not in p for p in data['products'][0]['forecast'])
    assert data['orders'][0]['da_ordinare'] >= 0


def test_override_applies():
    data = client.post('/api/forecast', json={'top_n': 1, 'overrides': True, 'lead_time': 40, 'cycle': 10}).json()
    assert len(data['products'][0]['forecast']) == 50
    assert data['products'][0]['params']['lead_time'] == 40


def test_validation_and_busy():
    assert client.post('/api/forecast', json={'top_n': 1000}).status_code == 422
    assert client.post('/api/forecast', json={'source': '../private'}).status_code == 422
    with calculation():
        assert client.post('/api/forecast', json={}).status_code == 409


def test_unavailable_source(monkeypatch):
    def fail(*a):
        raise FileNotFoundError('private-path')
    monkeypatch.setattr(api, 'source_fingerprint', fail)
    r = client.post('/api/forecast', json={'source': 'uci'})
    assert r.status_code == 503 and 'private-path' not in r.text


def test_report_whitelist():
    reports = client.get('/api/reports').json()['reports']
    assert reports
    assert client.get('/api/reports/'+reports[0]['id']).status_code == 200
    assert client.get('/api/reports/not-allowed').status_code == 404
    assert client.get('/api/not-found').status_code == 404
