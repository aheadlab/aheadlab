"""Matched causal capacity policies, independent of the forecasting model."""
import numpy as np
import pandas as pd


def reactive_guard(history, start, length, factor=1.25):
    """For target t, measurements through t-2 only (one-hour provisioning)."""
    y=np.asarray(history,dtype=float)
    if start<7 or length<1 or start+length>len(y) or factor<0:
        raise ValueError('Invalid reactive window')
    # Missing observations are not zeros; retain the last observed load.
    filled=pd.Series(y).ffill().fillna(0.)
    guarded=filled.rolling(6,min_periods=1).max().shift(2).fillna(0.)
    return guarded.to_numpy()[start:start+length]*factor


def margins(actual, prediction, q, rolling=False, window=14):
    actual,prediction=np.asarray(actual,float),np.asarray(prediction,float)
    if actual.shape!=prediction.shape or actual.ndim!=2 or not 0<=q<=1:
        raise ValueError('Invalid calibration arrays')
    result=np.full(len(actual),np.nan)
    residual=actual-prediction
    for day in range(14,len(actual)):
        past=residual[max(0,day-window):day] if rolling else residual[:14]
        valid=past[np.isfinite(past)]
        if not len(valid):raise ValueError('No past calibration errors')
        result[day]=max(0.,float(np.quantile(valid,q)))
    return result


def simulate(prediction, actual, valid, unit, margin, guard, initial, start=14):
    """Return daily cost/deficit/demand and full capacity, with continuous state."""
    p,y=np.asarray(prediction,float),np.asarray(actual,float)
    margin=np.asarray(margin,float);guard=np.asarray(guard,float)
    if p.shape!=y.shape or p.shape!=guard.shape or p.ndim!=2 or p.shape[1]!=24:
        raise ValueError('Expected matching day/hour arrays')
    if len(margin)!=len(p) or len(valid)!=len(p) or unit<=0 or initial<1:
        raise ValueError('Invalid capacity inputs')
    if not np.isfinite(p).all() or (p<0).any() or not np.isfinite(guard).all() or (guard<0).any():
        raise ValueError('Invalid forecast or guard')
    if not np.isfinite(margin[start:]).all() or (margin[start:]<0).any():
        raise ValueError('Invalid margin')
    full=np.zeros_like(p,dtype=np.int64);daily=np.full((3,len(p)-start),np.nan)
    previous=int(initial)
    for day in range(start,len(p)):
        units=np.maximum(1,np.ceil((p[day]+margin[day])/unit)).astype(np.int64)
        units[0]=previous
        units=np.maximum(units,np.ceil(guard[day]/unit).astype(np.int64))
        previous=int(units[-1]);full[day]=units
        if valid[day]:
            truth=y[day]/unit
            if not np.isfinite(truth).all():raise ValueError('Missing target marked valid')
            daily[:,day-start]=[units.sum(),np.maximum(truth-units,0).sum(),truth.sum()]
    return daily,full


def candidates():
    original=[dict(family='original',q=q,multiplier=1.,reactive=0.)
        for q in [0.,.5,.75,.9,.95,.975,.99,1.]]
    adaptive=[dict(family='adaptive',q=q,multiplier=factor,reactive=guard)
        for q in [.95,.99,1.] for factor in [1.,1.5,2.] for guard in [0.,1.25]]
    return original+adaptive


def select(rows):
    feasible=[r for r in rows if r['deficit_fraction']<=.01]
    return min(feasible or rows,key=lambda r:(r['unit_hours'],r['deficit_fraction']) if feasible
        else (r['deficit_fraction'],r['unit_hours']))


def bootstrap(ai,baseline,repetitions=2000,seed=20261107):
    a,b=np.asarray(ai),np.asarray(baseline)
    if a.shape!=b.shape or a.ndim!=3 or a.shape[1]!=3 or not np.array_equal(np.isnan(a),np.isnan(b)):
        raise ValueError('Invalid paired observations')
    rng=np.random.default_rng(seed);series,_,days=a.shape;draws=[]
    for _ in range(repetitions):
        ids=rng.integers(series,size=series)
        starts=rng.integers(days,size=int(np.ceil(days/7)))
        hours=((starts[:,None]+np.arange(7))%days).ravel()[:days]
        av=np.nansum(a[ids][:,:,hours],axis=(0,2));bv=np.nansum(b[ids][:,:,hours],axis=(0,2))
        draws.append([100*(1-av[0]/bv[0]),av[1]/av[2]-bv[1]/bv[2]])
    ci=np.quantile(draws,[.025,.975],axis=0)
    return dict(saving_ci=ci[:,0].tolist(),deficit_delta_ci=ci[:,1].tolist())
