#!/usr/bin/env python
"""Offline synthetic default; real UCI and model downloads require opt-in."""
import argparse
import hashlib
import json
import platform
import time
from pathlib import Path
import numpy as np
import pandas as pd
from stocksense.demo import synthetic_transactions, simulated_stock, SEED
from stocksense.ingest import converti_una_volta, RAW
from stocksense.prepare import pulisci, vendite_giornaliere
from stocksense.forecast_all import BASELINES, forecast
from stocksense.backtest import origins, rolling_backtest
from stocksense.simulation import simulate
from stocksense.config import load_config, for_sku
from stocksense.logic import calcola_riordino


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--quick', action='store_true')
    parser.add_argument('--data', choices=['synthetic', 'uci'], default='synthetic')
    parser.add_argument('--model', choices=['baseline', '5M', '28M', '209M'], default='baseline')
    parser.add_argument('--output', type=Path, default=Path('results/baseline'))
    args = parser.parse_args()
    started = time.perf_counter()
    folds, horizon, step, top, days = (2, 28, 28, 2, 28) if args.quick else (8, 30, 30, 50, 180)
    raw = synthetic_transactions(products=50) if args.data == 'synthetic' else converti_una_volta()
    clean = pulisci(raw)
    calendar = pd.date_range(clean.giorno.min(), clean.giorno.max())
    first = min(origins(len(calendar), folds, horizon, step)[0], len(calendar)-days)
    daily = vendite_giornaliere(clean, top, calendar[first])
    models = list(BASELINES) + ([] if args.model == 'baseline' else [args.model])
    config = load_config()
    scores, summary = rolling_backtest(daily, models, folds, horizon, step)
    ledger, inventory = simulate(daily, len(daily)-days, models, config)
    stock = simulated_stock(daily)
    orders = []
    for model in models:
        for sku in daily:
            params = for_sku(config, sku)
            pred = forecast(daily[sku].to_numpy(), max(30, params['lead_time']+params['ciclo']), model)
            orders.append(dict(sku=sku, modello=model, data_ordine=daily.index[-1]+pd.Timedelta(days=1),
                               arrivo_previsto=daily.index[-1]+pd.Timedelta(days=1+params['lead_time']),
                               **calcola_riordino(pred, stock[sku], **params)))
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    for name, frame in [('backtest', scores), ('riepilogo', summary), ('simulazione', inventory),
                        ('inventario_giornaliero', ledger), ('ordini', pd.DataFrame(orders))]:
        frame.to_csv(out/f'{name}.csv', index=False)
    pd.DataFrame({'sku': daily.columns, 'quota_giorni_vendita_training':
                  (daily.iloc[:first] > 0).mean().to_numpy()}).to_csv(out/'diagnostica.csv', index=False)
    metadata = dict(data=args.data, inventario='SIMULATO, seed 42; non giacenze UCI',
                    mode='smoke' if args.quick else 'full', models=models, seed=SEED,
                    folds=folds, horizon=horizon, step=step, skus=list(daily.columns),
                    selection_cutoff=str(calendar[first]), inventory_days=days,
                    raw_rows=len(raw), clean_rows=len(clean), python=platform.python_version(),
                    elapsed_seconds=time.perf_counter()-started, config=config,
                    clipping='99.5 percentile training-only; target and MASE scale raw',
                    inventory_timing='receive, review before demand, consume; no backlog',
                    quantiles='marginal sums heuristic; baselines point only',
                    ties='all tied minima win; undefined MASE excluded',
                    source_sha256=hashlib.sha256(RAW.read_bytes()).hexdigest() if args.data == 'uci' else None)
    (out/'metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    # Portable SVG without browser / Kaleido dependency.
    bars = []
    maximum = max(float(inventory.vendite_perse.max()), 1)
    for i, row in enumerate(inventory.itertuples()):
        y = 65+i*48
        bars.append(f'<text x="10" y="{y+16}">{row.modello}</text><rect x="160" y="{y}" width="{400*row.vendite_perse/maximum}" height="25" fill="#3579ae"/><text x="570" y="{y+16}">{row.vendite_perse:.1f}</text>')
    (out/'vendite_perse.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="720" height="320"><rect width="100%" height="100%" fill="white"/><text x="10" y="25">Vendite perse — inventario SIMULATO — '+args.data+' — '+metadata['mode']+'</text>'+''.join(bars)+'</svg>', encoding='utf-8')
    print(summary.to_string(index=False))
    print(inventory.to_string(index=False))
    print(f'Outputs: {out}; {metadata["elapsed_seconds"]:.1f}s')


if __name__ == '__main__':
    main()
