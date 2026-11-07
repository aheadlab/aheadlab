import numpy as np
import pytest
from capacityplanner.core import fill_past, predict, plan, evaluate, demo
from fastapi.testclient import TestClient
from capacityplanner.api import app


def test_gap_fill_is_prefix_only():
    a = np.arange(200,dtype=float); a[190:193] = np.nan
    b = a.copy(); b[193:] = 999999
    np.testing.assert_equal(fill_past(a)[:193],fill_past(b)[:193])


@pytest.mark.parametrize('method',['last','daily','weekly','weekly_mean','ets','mstl','ridge'])
def test_baselines_do_not_modify_input(method):
    y = demo().to_numpy()[-600:]; before=y.copy()
    p=predict(y,method)
    assert p['median'].shape == (24,)
    assert (p['median']>=0).all()
    np.testing.assert_equal(y,before)


def test_startup_delay_and_conservation():
    units=plan([100,200,50],100,initial_units=1,startup_hours=1)
    np.testing.assert_equal(units,[1,2,1])
    r=evaluate([120,150,80],units,100)
    assert r['deficit']==20 and r['unit_hours']==4 and r['idle']==70
    assert r['demand']-r['deficit']+r['idle']==sum(units)*100


def test_initial_capacity_has_no_future_access():
    assert plan([900,100],100,initial_units=2)[0]==2
    assert plan([100,100],100,initial_units=2)[0]==2


@pytest.mark.parametrize('args', [([1,2],0),([np.nan,2],1),([-1,2],1)])
def test_invalid_plans(args):
    with pytest.raises(ValueError):plan(*args)


def test_api_demo_and_validation():
    client=TestClient(app)
    assert client.get('/api/health').status_code==200
    r=client.post('/api/forecast',json={'model':'weekly'}); assert r.status_code==200
    value=r.json(); assert len(value['forecast'])==24
    assert value['source']=='synthetic' and value['metrics']['unit_hours']>=24
    assert client.post('/api/forecast',json={'throughput':0}).status_code==422
    assert client.post('/api/forecast',json={'startup_hours':7}).status_code==422
    assert client.post('/api/forecast',json={'source':'cesnet','series':'../x'}).status_code==404


def test_api_preserves_zero_cost():
    r=TestClient(app).post('/api/forecast',json={'unit_cost':0}).json()
    assert r['metrics']['cost']==0


def test_ridge_recovers_constant_signal():
    p=predict(np.full(500,37.),'ridge')['median']
    np.testing.assert_allclose(p,37.,atol=1e-7)


def test_policy_selection_obeys_service_constraint():
    from capacityplanner.benchmark import choose
    candidates=[dict(unit_hours=10,deficit_fraction=.2),dict(unit_hours=20,deficit_fraction=.005),
                dict(unit_hours=30,deficit_fraction=.001)]
    assert choose(candidates)==candidates[1]


def test_bootstrap_is_paired():
    from capacityplanner.benchmark import paired_intervals
    a=np.array([[[10.,20.],[.1,.2],[100.,200.]],[[20.,30.],[.2,.3],[200.,300.]]])
    saving,delta=paired_intervals(a,a,100)
    np.testing.assert_allclose(saving,[0,0]);np.testing.assert_allclose(delta,[0,0])


def test_missing_targets_are_not_free_capacity():
    from capacityplanner.benchmark import simulate_policy
    r=simulate_policy(np.ones((2,24))*10,np.ones((2,24))*10,[True,False],10,0,1)
    assert np.isnan(r[:,1]).all()
    assert r[0,0]==24 and r[1,0]==0 and r[2,0]==24
