"""SolarCast retrospective workspace API; no synthetic current forecast claims."""
from pathlib import Path
from functools import lru_cache
from datetime import date
from typing import Literal
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .api_support import calculation, response, install_common, install_frontend
from .demo import synthetic
from .ingest import historical_dataset
from .forecast import forecast
from .logic import fasce_migliori

ROOT = Path(__file__).resolve().parents[2]
app = FastAPI(title='SolarCast API', version='1.0.0')
install_common(app, 'solarcast', ROOT)


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source: Literal['synthetic', 'pvgis'] = 'synthetic'
    model: Literal['baseline', '5M', '28M', '209M'] = 'baseline'
    method: Literal['seasonal_naive24', 'radiation_regression', 'A', 'B'] = 'seasonal_naive24'
    lat: float = Field(default=45.82, ge=-90, le=90, allow_inf_nan=False)
    lon: float = Field(default=8.83, ge=-180, le=180, allow_inf_nan=False)
    kwp: float = Field(default=6, gt=0, le=10000, allow_inf_nan=False)
    angle: int = Field(default=30, ge=0, le=90)
    aspect: int = Field(default=0, ge=-180, le=180)
    year: int = Field(default=2023, ge=2006, le=2023)
    origin: date | None = None
    max_context: int = Field(default=720, ge=24, le=32768)
    threshold: float | None = Field(default=None, ge=0, le=10000, allow_inf_nan=False)
    min_hours: int = Field(default=2, ge=1, le=24)

    @model_validator(mode='after')
    def model_method(self):
        if self.method in ('A', 'B') and self.model == 'baseline':
            raise ValueError('A/B richiedono una taglia Timestral')
        return self


@lru_cache(maxsize=4)
def dataset(source, lat, lon, year, angle, aspect):
    return synthetic(year) if source == 'synthetic' else historical_dataset(
        lat, lon, year, angle, aspect, cache_dir=ROOT/'data/raw')


@app.get('/api/meta')
def meta():
    return {'app': 'solarcast', 'models': ['baseline', '5M', '28M', '209M'],
            'sources': ['synthetic', 'pvgis'], 'defaults': Request().model_dump(),
            'methods': ['seasonal_naive24', 'radiation_regression', 'A', 'B']}


@app.post('/api/forecast')
def calculate(req: Request):
    with calculation():
        data = dataset(req.source, req.lat, req.lon, req.year, req.angle, req.aspect)
        origin = pd.Timestamp(req.origin or date(req.year, 6, 15), tz='UTC')
        history = data.loc[data.index < origin]
        future = data.loc[origin:origin+pd.Timedelta(hours=47)]
        if len(history) < 24 or len(future) != 48:
            raise HTTPException(422, 'Origine fuori dal periodo disponibile o storico insufficiente')
        result = forecast(history, future.drop(columns='kwh'), req.method,
                          '5M' if req.model == 'baseline' else req.model, req.max_context)
        frame = result.frame
        windows = fasce_migliori(frame['median'], frame.get('p10'), frame.index,
                                req.kwp, req.threshold, req.min_hours)
        rows = []
        for time, row in frame.iterrows():
            point = dict(time=time, median=row['median']*req.kwp,
                         radiation=future.loc[time, 'shortwave_radiation'], actual=future.loc[time, 'kwh']*req.kwp)
            if 'p10' in frame:
                point.update(lower=row.p10*req.kwp, upper=row.p90*req.kwp)
            rows.append(point)
        days = []
        for time, part in frame.groupby(frame.index.floor('D')):
            row = dict(date=time, energy=float(part['median'].sum()*req.kwp))
            if 'p10' in part:
                row.update(lower=float(part.p10.sum()*req.kwp), upper=float(part.p90.sum()*req.kwp))
            days.append(row)
        return response(dict(app='solarcast', source=req.source, model=result.metadata['model'],
            as_of=history.index[-1], origin=origin, kwp=req.kwp, method=req.method,
            metrics=dict(energy=sum(r['energy'] for r in days), peak=float(frame['median'].max()*req.kwp),
                         windows=len(windows), window_hours=sum(w['hours'] for w in windows)),
            history=[dict(time=t, value=v*req.kwp) for t,v in history.kwh.iloc[-48:].items()],
            forecast=rows, windows=windows, days=days,
            metadata=dict(**result.metadata, source=req.source, retrospective=True,
                          interval='Somme marginali euristiche, non intervalli calibrati',
                          units_display='kWh per ora, capacità applicata una sola volta')))


install_frontend(app, ROOT)
