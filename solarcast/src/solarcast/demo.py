"""Deterministic two-year retrospective, not a weather forecast."""
import numpy as np
import pandas as pd


def synthetic(year=2023, seed=42):
    idx = pd.date_range(f'{year-1}-01-01', f'{year+1}-01-01', freq='h', tz='UTC', inclusive='left')
    rng = np.random.default_rng(seed)
    days = pd.date_range(idx[0], idx[-1].floor('D'), freq='D')
    regime = np.empty(len(days))
    regime[0] = 20
    for i in range(1, len(days)):
        regime[i] = regime[i-1] if rng.random() < .65 else rng.choice([10, 50, 90])
    cloud = np.clip(np.repeat(regime, 24) + rng.normal(0, 8, len(idx)), 0, 100)
    season = np.cos(2*np.pi*(idx.dayofyear.to_numpy()-172)/365.25)
    daylight = 12 + 3.5*season
    sun = np.maximum(0, np.cos(np.pi*(idx.hour.to_numpy()-11.5)/daylight))
    sun[np.abs(idx.hour.to_numpy()-11.5) >= daylight/2] = 0
    radiation = (650+250*season)*sun*(1-.008*cloud)
    temp = 13+11*season+4*sun+rng.normal(0, 1, len(idx))
    target = np.maximum(0, radiation/1000*.88*(1-.003*(temp-20)))
    return pd.DataFrame(dict(kwh=target, shortwave_radiation=radiation, cloud_cover=cloud,
                             temperature_2m=temp), index=idx)
