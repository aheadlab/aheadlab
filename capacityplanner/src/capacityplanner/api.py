"""Local demo/replay HTTP interface. Does not alter running infrastructure."""
import json
from pathlib import Path
from functools import lru_cache
from typing import Literal
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from .core import MODELS, demo, predict, plan, evaluate
from .api_support import calculation, response, install_frontend

ROOT = Path(__file__).resolve().parents[2]
app = FastAPI(title='Capacity Planner',version='0.1.0')


def research():
    path = ROOT/'results/cesnet/report.json'
    return json.loads(path.read_text()) if path.exists() else {'status':'pending','series':[]}


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source: Literal['synthetic','cesnet'] = 'synthetic'
    series: str = Field(default='',max_length=80)
    model: Literal['last','daily','weekly','weekly_mean','ets','mstl','ridge','5M','28M'] = 'weekly'
    throughput: float = Field(default=250,ge=.000001,le=1e15)
    margin_pct: float = Field(default=15,ge=0,le=200)
    startup_hours: int = Field(default=1,ge=0,le=6)
    unit_cost: float = Field(default=.05,ge=0,le=1000)


@app.get('/api/health')
def health():
    return {'status':'ok','app':'capacityplanner'}


@app.get('/api/meta')
def meta():
    r = research()
    return dict(models=list(MODELS),defaults=Request().model_dump(),
                series=r.get('series',[]),research_available=r.get('status')=='complete')


@app.get('/api/research')
def report():
    return response(research())


@lru_cache(maxsize=16)
def synthetic_forecast(model):
    series = demo()
    return series,predict(series.iloc[:-24].to_numpy(),model)


@app.post('/api/forecast')
def forecast(req:Request):
    with calculation():
        if req.source == 'synthetic':
            series, prediction = synthetic_forecast(req.model)
            history = series.iloc[-192:-24]
            actual = series.iloc[-24:].to_numpy()
            times = [str(t) for t in series.index[-24:]]
            observed = [dict(time=str(t),value=float(v)) for t,v in history.items()]
            values = prediction['median']
            unit = req.throughput
            label = 'Demo sintetica · replay di 24 ore'
        else:
            r = research()
            record = r.get('replays',{}).get(req.series)
            if record is None:
                raise HTTPException(404,'Serie CESNET non disponibile')
            if req.model not in record['forecasts']:
                raise HTTPException(404,'Previsione non disponibile per questo modello')
            prediction = record['forecasts'][req.model]
            values = np.array(prediction['median'])
            actual = np.array(record['actual'])
            times, observed = record['times'], record['history']
            unit = req.throughput
            label = f'CESNET · {req.series} · replay storico'
        margin = req.margin_pct/100*unit
        initial = max(1,int(np.ceil(observed[-1]['value']/unit)))
        units = plan(values,unit,margin,initial,req.startup_hours)
        fixed = np.full(24,initial)
        score = evaluate(actual,units,unit)
        reference = evaluate(actual,fixed,unit)
        rows = [dict(time=times[i],median=float(values[i]),actual=float(actual[i]),
                     lower=float(prediction['p10'][i]) if 'p10' in prediction else None,
                     upper=float(prediction['p90'][i]) if 'p90' in prediction else None,
                     capacity=float(units[i]*unit),units=int(units[i]),
                     deficit=float(max(actual[i]-units[i]*unit,0))) for i in range(24)]
        return response(dict(source=req.source,source_label=label,model=req.model,history=observed,
            forecast=rows,metrics={**score,'cost':score['unit_hours']*req.unit_cost},
            reference={**reference,'cost':reference['unit_hours']*req.unit_cost},
            parameters=req.model_dump(),unit='Mbit/s medi' if req.source=='cesnet' else 'richieste/ora',
            disclaimer='Simulazione oraria: il deficit non misura latenza, pacchetti persi o SLA. Costi ipotetici.'))


install_frontend(app,ROOT)
