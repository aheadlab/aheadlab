"""CloudGuard local web API. No AWS access or notification sends through HTTP."""
from pathlib import Path
from typing import Literal
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from .api_support import calculation, response, install_common, install_frontend
from .synthetic import genera_costi
from .prepare import tabella_giornaliera
from .logic import forecast, stima_fine_mese
from .backtest import benchmark_anomalies

ROOT = Path(__file__).resolve().parents[2]
app = FastAPI(title='CloudGuard API', version='1.0.0')
install_common(app, 'cloudguard', ROOT)


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid')
    service: str = Field(default='Amazon EC2', max_length=100)
    model: Literal['baseline', '5M', '28M', '209M'] = 'baseline'
    horizon: int = Field(default=30, ge=1, le=90)
    cutoff_days: int = Field(default=7, ge=0, le=28)


@app.get('/api/meta')
def meta():
    raw, _ = genera_costi()
    return {'app': 'cloudguard', 'models': ['baseline', '5M', '28M', '209M'],
            'sources': ['synthetic'], 'services': sorted(raw.servizio.unique()),
            'defaults': Request().model_dump(), 'currency': 'USD'}


@app.post('/api/forecast')
def calculate(req: Request):
    with calculation():
        raw, events = genera_costi()
        table = tabella_giornaliera(raw)
        if req.service not in table:
            raise HTTPException(422, 'Servizio sconosciuto')
        table = table.iloc[:-req.cutoff_days] if req.cutoff_days else table
        series = table[req.service]
        prediction = forecast(series.to_numpy(), req.horizon, req.model)
        median = np.asarray(getattr(prediction, 'mediana', prediction))
        dates = pd.date_range(series.index[-1]+pd.Timedelta(days=1), periods=req.horizon)
        rows = []
        for i, time in enumerate(dates):
            row = dict(time=time, median=median[i])
            if hasattr(prediction, 'p10'):
                row.update(lower=prediction.p10[i], upper=prediction.p90[i])
            rows.append(row)
        month = stima_fine_mese(series, req.model)
        _, detail = benchmark_anomalies(table[[req.service]], events, req.model, days=30)
        alerts = detail.loc[detail.anomalia].to_dict('records')
        services = [dict(service=name, total=float(table[name].iloc[-30:].sum()),
                         latest=float(table[name].iloc[-1])) for name in table]
        return response(dict(app='cloudguard', source='synthetic', model=req.model,
            as_of=series.index[-1], currency='USD', service=req.service, services=services,
            metrics=dict(spent=month['speso'], estimate=month['stima'],
                         forecast_total=float(median.sum()), alerts=len(alerts)), month=month,
            history=[dict(time=t, value=v) for t,v in series.iloc[-90:].items()],
            forecast=rows, alerts=alerts,
            metadata=dict(synthetic=True, provisional=False, interval='Somma quantili euristica, non calibrata',
                          alert_period='Ultimi 30 giorni, confronto retrospettivo con regola 3-sigma',
                          sends_enabled=False)))


install_frontend(app, ROOT)
