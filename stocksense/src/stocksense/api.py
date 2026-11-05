"""StockSense web API. Order proposals only: no supplier-side mutations."""
from pathlib import Path
from functools import lru_cache
from typing import Literal
import numpy as np
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field
from .api_support import calculation, response, install_common, install_frontend
from .demo import synthetic_transactions, simulated_stock
from .ingest import converti_una_volta, source_fingerprint
from .prepare import pulisci, vendite_giornaliere
from .config import load_config, for_sku
from .forecast_all import forecast
from .logic import calcola_riordino

ROOT = Path(__file__).resolve().parents[2]
app = FastAPI(title='StockSense API', version='1.0.0')
install_common(app, 'stocksense', ROOT)


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source: Literal['synthetic', 'uci'] = 'synthetic'
    model: Literal['seasonal_naive', 'moving_average', 'auto_ets', '5M', '28M', '209M'] = 'moving_average'
    lead_time: int = Field(default=14, ge=1, le=90)
    cycle: int = Field(default=7, ge=1, le=30)
    min_lot: int = Field(default=1, ge=1, le=10000)
    level: Literal['p90', 'p99', 'mediana'] = 'p90'
    overrides: bool = False
    top_n: int = Field(default=50, ge=1, le=50)


@lru_cache(maxsize=4)
def dataset(source, fingerprint):
    raw = synthetic_transactions(products=50) if source == 'synthetic' else converti_una_volta(
        ROOT/'data/raw/online_retail_II.xlsx', ROOT/'data/processed/transazioni.parquet')
    return pulisci(raw)


@app.get('/api/meta')
def meta():
    return {'app': 'stocksense', 'models': ['moving_average', 'seasonal_naive', 'auto_ets', '5M', '28M', '209M'],
            'sources': ['synthetic', 'uci'], 'defaults': Request().model_dump(),
            'uci_available': (ROOT/'data/raw/online_retail_II.xlsx').is_file()}


@app.post('/api/forecast')
def calculate(req: Request):
    with calculation():
        fingerprint = source_fingerprint(ROOT/'data/raw/online_retail_II.xlsx') if req.source == 'uci' else 'synthetic-v1'
        clean = dataset(req.source, fingerprint)
        cutoff = clean.giorno.max()-pd.Timedelta(days=239)
        daily = vendite_giornaliere(clean, req.top_n, cutoff)
        descriptions = clean.drop_duplicates('StockCode').set_index('StockCode').Description.to_dict()
        config = load_config(ROOT/'config/prodotti.csv')
        stock = simulated_stock(daily)
        asof = daily.index[-1]+pd.Timedelta(days=1)
        orders, products = [], []
        for sku in daily:
            params = for_sku(config, sku)
            if req.overrides:
                params.update(lead_time=req.lead_time, ciclo=req.cycle, livello=req.level, lotto_minimo=req.min_lot)
            horizon = max(30, params['lead_time']+params['ciclo'])
            pred = forecast(daily[sku].to_numpy(), horizon, req.model)
            decision = calcola_riordino(pred, stock[sku], **params)
            orders.append(dict(sku=sku, description=descriptions.get(sku, sku),
                               order_date=asof, arrival_date=asof+pd.Timedelta(days=params['lead_time']),
                               **decision))
            dates = pd.date_range(asof, periods=horizon)
            points = []
            projected = np.maximum(stock[sku]-np.cumsum(pred.mediana), 0)
            for i, date in enumerate(dates):
                row = dict(time=date, median=pred.mediana[i], stock=projected[i])
                if hasattr(pred, 'p10'):
                    row.update(lower=pred.p10[i], upper=pred.p90[i])
                points.append(row)
            products.append(dict(sku=sku, description=descriptions.get(sku, sku), params=params,
                history=[dict(time=t, value=v) for t,v in daily[sku].iloc[-120:].items()], forecast=points))
        priority = {'URGENTE': 0, 'DA ORDINARE': 1, 'OK': 2}
        orders.sort(key=lambda row: (priority[row['urgenza']], row['sku']))
        return response(dict(app='stocksense', source=req.source, model=req.model, as_of=asof,
            metrics=dict(products=len(orders), urgent=sum(r['urgenza']=='URGENTE' for r in orders),
                         order_units=sum(r['da_ordinare'] for r in orders), stock=sum(stock.values())),
            orders=orders, products=products,
            metadata=dict(inventory='SIMULATO, seed 42', selection_cutoff=cutoff,
                          orders_sent=False, overrides=req.overrides,
                          interval='Quantili marginali: nessun livello di servizio aggregato garantito')))


install_frontend(app, ROOT)
