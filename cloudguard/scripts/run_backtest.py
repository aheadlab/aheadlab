"""Run from the standalone repository after pip install -e ."""
import argparse
import json
import platform
from pathlib import Path
import numpy as np
import pandas as pd
from cloudguard.synthetic import genera_costi, END_DATE
from cloudguard.prepare import tabella_giornaliera
from cloudguard.backtest import benchmark_forecast, benchmark_anomalies
from cloudguard.logic import MODELS


def main():
    parser = argparse.ArgumentParser(description="CloudGuard: benchmark sintetico riproducibile")
    parser.add_argument("--quick", action="store_true", help="smoke: un servizio, 2 fold, 30 giorni anomalie")
    parser.add_argument("--model", choices=MODELS, default="baseline")
    parser.add_argument("--output", type=Path, default=Path("results"))
    args = parser.parse_args()
    raw, events = genera_costi()
    folds, days = (2, 30) if args.quick else (20, 300)
    dates = pd.date_range(raw.data.min(), raw.data.max(), freq='D')
    first = min(len(dates)-30-(folds-1)*7, len(dates)-days)
    selection_end = dates[first-1]
    table = tabella_giornaliera(raw, selection_end=selection_end)
    if args.quick:
        table = table.iloc[:, :1]
    forecasts = benchmark_forecast(table, args.model, folds=folds)
    anomalies, detail = benchmark_anomalies(table, events, args.model, days=days)
    args.output.mkdir(parents=True, exist_ok=True)
    for name, frame in [("backtest", forecasts), ("anomalies", anomalies), ("anomaly_days", detail), ("events", events)]:
        frame.to_csv(args.output / f"{name}.csv", index=False)
    metadata = dict(dataset="synthetic", seed=7, end_date=END_DATE, days=400,
                    services=list(table.columns), mode="smoke" if args.quick else "full",
                    model=args.model, folds=folds, step=7, horizons=[7, 30], anomaly_days=days,
                    selection_end=str(selection_end),
                    currency="USD", python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
                    interval="Actual model marginal quantiles only; baseline has no coverage",
                    event_denominator="events intersecting evaluated service/date pairs")
    (args.output / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    summary = forecasts.groupby(["modello", "h"]).mae.mean()
    maximum = max(float(summary.max()), 1.)
    elements = ['<svg xmlns="http://www.w3.org/2000/svg" width="760" height="400"><rect width="100%" height="100%" fill="white"/>',
                '<text x="10" y="25">CloudGuard — MAE medio USD, dati sintetici</text>']
    for i, ((model, h), value) in enumerate(summary.items()):
        y = 60+i*40
        elements.append(f'<text x="10" y="{y+16}">{model} h={h}</text><rect x="230" y="{y}" width="{400*value/maximum:.1f}" height="23" fill="steelblue"/><text x="640" y="{y+16}">{value:.3f}</text>')
    (args.output / "benchmark.svg").write_text("\n".join(elements)+"</svg>", encoding="utf-8")
    print(forecasts.groupby(["modello", "h"])[["mae", "mase", "coverage80"]].mean().to_string())
    print(anomalies.to_string(index=False))


if __name__ == "__main__":
    main()
