"""Daily lost-sales ledger: receive, review (past only), consume, close."""
import numpy as np
import pandas as pd
from .forecast_all import forecast
from .logic import calcola_riordino, nonnegative
from .config import for_sku
from .demo import simulated_stock
from .baselines import _integer
from .prepare import validate_daily


def simulate(daily, start, models, config=None, initial_stock=None, predictor=forecast):
    validate_daily(daily)
    start = _integer(start, 'start')
    if start >= len(daily) or not np.isfinite(daily.to_numpy()).all() or (daily < 0).any().any():
        raise ValueError('Need nonnegative finite demand and a training prefix')
    config = config or {}
    initial_stock = simulated_stock(daily.iloc[:start]) if initial_stock is None else initial_stock
    rows = []
    for model in models:
        for sku in daily:
            stock = nonnegative(initial_stock[sku], 'initial_stock')
            pending = []
            params = for_sku(config, sku)
            cycle = _integer(params['ciclo'], 'ciclo')
            lead = _integer(params['lead_time'], 'lead_time')
            for t in range(start, len(daily)):
                arrived = sum(q for due, q in pending if due == t)
                pending = [(due, q) for due, q in pending if due > t]
                stock += arrived
                order = 0
                if (t-start) % cycle == 0:
                    pred = predictor(daily[sku].iloc[:t].to_numpy(), max(30, lead+cycle), model)
                    order = calcola_riordino(pred, stock, sum(q for _, q in pending), **params)['da_ordinare']
                    if order:
                        pending.append((t+lead, order))
                demand = float(daily[sku].iloc[t])
                sold = min(stock, demand)
                stock -= sold
                rows.append(dict(data=daily.index[t], sku=sku, modello=model,
                                 domanda=demand, vendite=sold, vendite_perse=demand-sold,
                                 stockout=int(demand > sold), giacenza=stock, arrivi=arrived,
                                 ordine=order, in_arrivo=sum(q for _, q in pending)))
    ledger = pd.DataFrame(rows)
    summary = ledger.groupby('modello', as_index=False).agg(
        giorni_stockout=('stockout', 'sum'), vendite_perse=('vendite_perse', 'sum'),
        giacenza_media=('giacenza', 'mean'))
    return ledger, summary
