from fastapi.testclient import TestClient
import numpy as np
import pandas as pd
from carbonshift import api
client=TestClient(api.app)

def request():return dict(case_id=api.replays()[0]['id'],comparator='GBM',duration=4,deadline=96,energy_kwh=1000)

def test_plan_matches_archived_decision_and_units():
    req=request();response=client.post('/api/plan',json=req)
    assert response.status_code==200
    result=response.json();saved=api.replays()[0]['plans']['Timestral-5M']
    assert result['plans']['Timestral-5M']['start']==saved['start']
    assert abs(result['plans']['Timestral-5M']['attributed_kg']-saved['attributed_kg']*10)<1e-9

def test_changed_constraints_are_exploratory_and_respected():
    req=request();req.update(duration=8,deadline=24)
    result=client.post('/api/plan',json=req).json()
    assert not result['benchmark_configuration']
    assert all(p['stop']<=24 and p['duration']==8 for p in result['plans'].values())

def test_unknown_replay_and_invalid_constraints():
    req=request();req['case_id']='unknown'
    assert client.post('/api/plan',json=req).status_code==404
    req=request();req.update(duration=20,deadline=4)
    assert client.post('/api/plan',json=req).status_code==422

def test_export_rows_match_horizon():
    response=client.post('/api/export',json=request())
    assert response.status_code==200 and len(response.text.splitlines())==97

def test_live_forecast_uses_history_only(monkeypatch):
    class Result:
        def quantile(self,q):return np.r_[np.ones(20)*30,np.ones(4)*5,np.ones(72)*30]
    class Model:
        def forecast(self,x,prediction_length):
            assert len(x)==168 and prediction_length==96
            return Result()
    monkeypatch.setattr(api,'model',lambda:Model())
    dates=pd.date_range('2026-01-01',periods=168,freq='h',tz='UTC')
    history=[dict(time=str(t),value=20) for t in dates]
    response=client.post('/api/forecast',json=dict(history=history))
    assert response.status_code==200 and response.json()['plan']['start']==20
    history[4]['time']=history[3]['time']
    assert client.post('/api/forecast',json=dict(history=history)).status_code==422
