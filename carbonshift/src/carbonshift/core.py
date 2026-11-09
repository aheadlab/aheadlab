"""Scheduling decisions consume forecasts only; realized values score decisions."""
import numpy as np

def vector(values):
    x=np.asarray(values,dtype=float)
    if x.ndim!=1 or not len(x) or not np.isfinite(x).all() or (x<0).any():
        raise ValueError('Servono valori finiti e non negativi')
    return x

def choose_window(forecast,duration=4,deadline=96):
    x=vector(forecast)
    if type(duration) is not int or type(deadline) is not int or not 1<=duration<=deadline<=len(x):
        raise ValueError('Durata e scadenza non valide')
    costs=np.convolve(x[:deadline],np.ones(duration)/duration,mode='valid')
    # Numerical roundoff must not send a flat forecast to an arbitrary late hour.
    choices=np.flatnonzero(np.isclose(costs,costs.min(),rtol=0,atol=1e-10))
    start=int(choices[0])
    return dict(start=start,stop=start+duration,expected_ci=float(costs[start]))

def score(actual,start,duration=4,energy_kwh=100):
    y=vector(actual)
    if type(start) is not int or type(duration) is not int or start<0 or duration<1 or start+duration>len(y):
        raise ValueError('Finestra non valida')
    if not np.isfinite(energy_kwh) or energy_kwh<=0:raise ValueError('Energia non valida')
    ci=float(y[start:start+duration].mean())
    return dict(actual_ci=ci,attributed_kg=energy_kwh*ci/1000,energy_kwh=float(energy_kwh),duration=duration)

def paired_interval(ai,classic,block=7,repetitions=5000,seed=20261109):
    a,b=np.asarray(ai,float),np.asarray(classic,float)
    if a.shape!=b.shape or a.ndim!=2 or not np.isfinite(a).all() or not np.isfinite(b).all() or (a<0).any() or (b<=0).any():
        raise ValueError('Confronti accoppiati non validi')
    rng=np.random.default_rng(seed);days=len(a);draws=[]
    for _ in range(repetitions):
        ix=((rng.integers(days,size=int(np.ceil(days/block)))[:,None]+np.arange(block))%days).ravel()[:days]
        draws.append(100*(1-a[ix].mean()/b[ix].mean()))
    return dict(saving_pct=float(100*(1-a.mean()/b.mean())),ci95=np.quantile(draws,[.025,.975]).tolist(),
        difference_g_per_kwh=float(b.mean()-a.mean()),days=days,zones=a.shape[1])
