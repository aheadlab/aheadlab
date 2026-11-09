"""Local replay planner and optional offline inference; no resource control."""
import csv,io,json,threading
from functools import lru_cache
from pathlib import Path
import numpy as np
import pandas as pd
from fastapi import FastAPI,HTTPException
from fastapi.responses import FileResponse,Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,ConfigDict,Field
from .core import choose_window,score

ROOT=Path(__file__).resolve().parents[2]
app=FastAPI(title='CarbonShift',version='0.1.0');lock=threading.Lock()
NAMES={'Timestral-5M':'Timestral 5M','GBM':'Gradient boosting','SARIMA':'SARIMA',
    'snaive_week':'Settimana precedente','yesterday':'Giorno precedente',
    'hourly_mean':'Profilo medio 28 giorni','fixed_hour':'Orario fisso','immediate':'Avvio immediato'}

@lru_cache(maxsize=1)
def replays():return json.loads((ROOT/'results/replays.json').read_text())

@app.get('/api/health')
def health():return dict(status='ok',app='carbonshift')

@app.get('/api/meta')
def meta():
    return dict(models=NAMES,comparators=['GBM','SARIMA','snaive_week','yesterday','hourly_mean','immediate'],
        cases=[{k:r[k] for k in ['id','zone','split','origin']} for r in sorted(replays(),key=lambda r:(r['zone'],r['origin']))])

@app.get('/api/research')
def research():
    r=json.loads((ROOT/'results/report.json').read_text())
    r['summary']=pd.read_csv(ROOT/'results/summary.csv').to_dict('records')
    r['zone_summary']=pd.read_csv(ROOT/'results/zone_summary.csv').to_dict('records')
    # A circular block equal to the entire sample cannot estimate uncertainty.
    r['results']['holdout']['block14']=None
    return r

class PlanRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    case_id:str=Field(min_length=1,max_length=40)
    comparator:str='GBM'
    duration:int=Field(default=4,ge=1,le=24,strict=True)
    deadline:int=Field(default=96,ge=4,le=96,strict=True)
    energy_kwh:float=Field(default=1000,gt=0,le=1e9,allow_inf_nan=False)

def calculate(req):
    record=next((r for r in replays() if r['id']==req.case_id),None)
    if record is None:raise HTTPException(404,'Replay non disponibile')
    if req.comparator not in ['GBM','SARIMA','snaive_week','yesterday','hourly_mean','immediate']:
        raise HTTPException(422,'Metodo di confronto non disponibile')
    if req.duration>req.deadline:raise HTTPException(422,'La durata supera la scadenza')
    plans={};truth=record['actual'];profiles=record['forecasts']
    for name in ['Timestral-5M',req.comparator]:
        plan=choose_window(profiles[name],req.duration,req.deadline) if name!='immediate' else dict(start=0,stop=req.duration,expected_ci=None)
        plans[name]={**plan,**score(truth,plan['start'],req.duration,req.energy_kwh)}
    a,b=plans['Timestral-5M'],plans[req.comparator]
    savings=100*(1-a['attributed_kg']/b['attributed_kg']) if b['attributed_kg'] else None
    return dict(case_id=record['id'],zone=record['zone'],origin=record['origin'],split=record['split'],
        times=record['times'][:req.deadline],actual=truth[:req.deadline],
        forecasts={m:v[:req.deadline] for m,v in profiles.items() if m in ['Timestral-5M',req.comparator]},
        plans=plans,comparator=req.comparator,saving_pct=savings,
        difference_kg=b['attributed_kg']-a['attributed_kg'],
        benchmark_configuration=req.duration==4 and req.deadline==96 and req.comparator=='GBM')

@app.post('/api/plan')
def plan(req:PlanRequest):return calculate(req)

@app.post('/api/export')
def export(req:PlanRequest):
    r=calculate(req);out=io.StringIO();writer=csv.writer(out)
    writer.writerow(['time_utc','actual_g_per_kwh','ai_forecast_g_per_kwh','classic_forecast_g_per_kwh','ai_active','classic_active'])
    a,b=r['plans']['Timestral-5M'],r['plans'][req.comparator]
    for i,t in enumerate(r['times']):
        writer.writerow([t,r['actual'][i],r['forecasts']['Timestral-5M'][i],
            r['forecasts'].get(req.comparator,['']*len(r['times']))[i],a['start']<=i<a['stop'],b['start']<=i<b['stop']])
    return Response(out.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=carbonshift-plan.csv'})

class Observation(BaseModel):
    model_config=ConfigDict(extra='forbid')
    time:str=Field(max_length=40)
    value:float=Field(ge=0,allow_inf_nan=False)

class ForecastRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    history:list[Observation]=Field(min_length=168,max_length=8192)
    duration:int=Field(default=4,ge=1,le=24,strict=True)
    deadline:int=Field(default=96,ge=4,le=96,strict=True)
    energy_kwh:float=Field(default=1000,gt=0,le=1e9,allow_inf_nan=False)

@lru_cache(maxsize=1)
def model():
    import os
    import torch
    from timestral import TimestralForecaster
    torch.set_num_threads(1)
    root=Path(os.environ.get('HF_HOME',Path.home()/'.cache/huggingface'))
    path=root/'hub/models--mistralai--Timestral-5M/snapshots/bdd20cfc15a3fea0e4cb5ccef37f8d3ca7aa335f'
    if not path.is_dir():raise FileNotFoundError('Pesi 5M locali assenti; consultare il README')
    return TimestralForecaster.from_pretrained(str(path),device='cpu',max_context=8192)

@app.post('/api/forecast')
def forecast(req:ForecastRequest):
    if req.duration>req.deadline:raise HTTPException(422,'La durata supera la scadenza')
    try:
        if any(pd.Timestamp(r.time).tzinfo is None for r in req.history):raise ValueError('Ogni timestamp deve indicare il fuso orario')
        dates=pd.DatetimeIndex(pd.to_datetime([r.time for r in req.history],utc=True,errors='raise'))
        if not (dates.to_series().diff().dropna()==pd.Timedelta(hours=1)).all():raise ValueError('La serie deve essere oraria, ordinata e senza buchi')
    except (ValueError,TypeError) as error:raise HTTPException(422,str(error)) from error
    if not lock.acquire(blocking=False):raise HTTPException(409,'Un calcolo è già in corso')
    try:
        x=np.array([r.value for r in req.history],dtype=np.float32)
        result=model().forecast(x,prediction_length=96)
        median=np.maximum(np.asarray(result.quantile(.5)).reshape(-1),0)
        selected=choose_window(median,req.duration,req.deadline)
        future=pd.date_range(dates[-1]+pd.Timedelta(hours=1),periods=req.deadline,freq='h')
        return dict(times=[str(t) for t in future],forecast=median[:req.deadline].tolist(),
            plan=selected,expected_kg=req.energy_kwh*selected['expected_ci']/1000,
            note='Stima su dati caricati; osservazioni future e beneficio effettivo non ancora disponibili.')
    except (ImportError,FileNotFoundError) as error:raise HTTPException(503,str(error)) from error
    finally:lock.release()

@app.get('/api/doc/{name}')
def document(name:str):
    paths={'research':ROOT/'docs/RESEARCH.md','protocol':ROOT/'docs/PROTOCOL.md',
        'math':ROOT/'docs/MATHEMATICS.md','decisions':ROOT/'results/decisions.csv'}
    if name not in paths or not paths[name].exists():raise HTTPException(404,'Documento non disponibile')
    return FileResponse(paths[name],filename=paths[name].name)

dist=ROOT/'web/dist'
if dist.is_dir():app.mount('/',StaticFiles(directory=dist,html=True),name='frontend')
