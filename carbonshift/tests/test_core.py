import numpy as np
import pytest
from carbonshift.core import choose_window,score,paired_interval

def test_same_energy_duration_and_deadline():
    p=np.full(96,30.);p[60:64]=5
    plan=choose_window(p)
    assert plan['start']==60 and plan['stop']==64
    result=score(p,plan['start'],energy_kwh=100)
    assert result==dict(actual_ci=5.,attributed_kg=.5,energy_kwh=100.,duration=4)

def test_noninterruptible_job_cannot_pick_scattered_cheap_hours():
    p=np.array([0,100,0,100,0,100,20,20,20,20],float)
    assert choose_window(p,4,10)['start']==6

def test_deadline_prevents_using_late_cheaper_window():
    p=np.full(96,10.);p[30:34]=1
    assert choose_window(p,4,24)['stop']<=24

def test_future_observations_do_not_enter_decision():
    forecast=np.arange(96,dtype=float)+1
    before=choose_window(forecast)
    first=score(np.ones(96),before['start'])
    second=score(np.ones(96)*100,before['start'])
    assert choose_window(forecast)==before and first['attributed_kg']!=second['attributed_kg']

def test_flat_forecast_chooses_earliest():
    assert choose_window(np.full(96,24.))['start']==0

@pytest.mark.parametrize('value',[[1,np.nan],[1,np.inf],[-1,1],[],[[1,2]]])
def test_invalid_series_rejected(value):
    with pytest.raises(ValueError):choose_window(value,1,1)

@pytest.mark.parametrize('duration,deadline',[(0,24),(25,24),(4,97),(4.0,24),(4,True)])
def test_invalid_constraints_rejected(duration,deadline):
    with pytest.raises(ValueError):choose_window(np.ones(96),duration,deadline)

def test_units_and_energy_scaling():
    a=score(np.full(96,200.),0,energy_kwh=100)
    b=score(np.full(96,200.),0,energy_kwh=1000)
    assert a['attributed_kg']==20 and b['attributed_kg']==200

def test_identical_decisions_zero_difference():
    a=np.ones((21,6))*20
    result=paired_interval(a,a,repetitions=30)
    assert result['saving_pct']==0 and result['ci95']==[0.,0.]

def test_bootstrap_preserves_common_zone_shocks():
    a=np.arange(1,22)[:,None]*np.arange(1,7)[None,:]
    result=paired_interval(a,a*2,repetitions=30)
    assert result['saving_pct']==50 and result['ci95']==[50.,50.]
