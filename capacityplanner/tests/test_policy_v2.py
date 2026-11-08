import numpy as np
import pytest
from capacityplanner.policy_v2 import reactive_guard,margins,simulate,select,bootstrap


def test_reaction_cannot_see_latest_unprovisionable_hour():
    y=np.ones(80);y[20]=100
    g=reactive_guard(y,10,60,1.)
    assert g[10]==1 and g[11]==1 and g[12]==100
    assert g[17]==100 and g[18]==1


def test_reactive_prefix_is_independent_of_future_observations():
    y=np.arange(120,dtype=float);changed=y.copy();changed[70:]=999999
    a=reactive_guard(y,20,100);b=reactive_guard(changed,20,100)
    np.testing.assert_array_equal(a[:52],b[:52])


@pytest.mark.parametrize('rolling',[False,True])
def test_margin_for_day_d_cannot_use_day_d_or_future(rolling):
    p=np.ones((40,24));y=p.copy();y[14]=30
    changed=y.copy();changed[20:]=1000
    a=margins(y,p,.99,rolling);b=margins(changed,p,.99,rolling)
    np.testing.assert_equal(a[:21],b[:21])
    assert a[14]==0
    if rolling:assert a[15]>0 and a[29]==0


def test_guard_costs_are_counted_and_state_crosses_midnight():
    p=np.ones((16,24))*10;y=p.copy();g=np.zeros_like(p);g[14,23]=80
    valid=np.ones(16,bool)
    daily,units=simulate(p,y,valid,10,np.zeros(16),g,1)
    assert units[14,23]==8 and units[15,0]==8
    assert daily[0,0]==31 and daily[0,1]==31
    assert daily[1].sum()==0


def test_missing_day_never_counts_as_zero_cost_or_demand():
    p=np.ones((16,24));y=p.copy();y[14,4]=np.nan
    valid=np.isfinite(y).all(axis=1)
    daily,_=simulate(p,y,valid,1,np.zeros(16),np.zeros_like(p),1)
    assert np.isnan(daily[:,0]).all() and daily[0,1]==24


def test_fixed_policy_matches_original_simulation():
    from capacityplanner.benchmark import simulate_policy
    rng=np.random.default_rng(7);p=rng.uniform(1,30,(30,24));y=rng.uniform(1,30,(30,24))
    valid=np.ones(30,bool);valid[20]=False
    a,_=simulate(p,y,valid,5,np.full(30,3),np.zeros_like(p),2)
    b=simulate_policy(p[14:],y[14:],valid[14:],5,3,2)
    np.testing.assert_allclose(a,b,equal_nan=True)


def test_selection_cannot_trade_away_service_to_save_capacity():
    rows=[dict(unit_hours=1,deficit_fraction=.02),dict(unit_hours=100,deficit_fraction=.005)]
    assert select(rows)==rows[1]


def test_identical_policies_have_zero_paired_intervals():
    a=np.ones((3,3,14));a[:,1,:]=0
    result=bootstrap(a,a,20)
    assert result==dict(saving_ci=[0.,0.],deficit_delta_ci=[0.,0.])
