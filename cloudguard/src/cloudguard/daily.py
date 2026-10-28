import argparse
import json
import pandas as pd
from .synthetic import genera_costi, END_DATE
from .ingest import scarica_costi_aws
from .prepare import tabella_giornaliera
from .logic import controlla_giorno, stima_fine_mese, MODELS
from .notify import invia_telegram


def run_daily(raw, *, as_of, model="baseline", send=False):
    cutoff = pd.Timestamp(as_of).normalize()-pd.Timedelta(days=2)
    raw = raw.loc[pd.to_datetime(raw['data']) <= cutoff].copy()
    for key in ('reported_dates', 'estimated_dates'):
        raw.attrs[key] = [d for d in raw.attrs.get(key, []) if pd.Timestamp(d) <= cutoff]
    table = tabella_giornaliera(raw, selection_end=cutoff-pd.Timedelta(days=1))
    results = []
    for service in table:
        series = table[service].loc[:cutoff]
        if series.empty:
            continue
        alert = controlla_giorno(series, model, as_of=as_of,
                                 provisional_dates=table.attrs.get("provisional_dates", ()))
        row = dict(servizio=service, valuta=table.attrs["valuta"], **alert)
        if alert["valutato"]:
            row["mese"] = stima_fine_mese(series, model)
        if alert["anomalia"]:
            month = row["mese"]
            text = (f"CloudGuard — anomalia\n{service} il {series.index[-1].date()}: "
                    f"{alert['reale']:.2f} {row['valuta']} (atteso {alert['atteso']:.2f}, soglia {alert['soglia']:.2f})\n"
                    f"Stima fine mese: {month['stima']:.2f}; banda euristica: {month['basso']} – {month['alto']}")
            row["notifica"] = invia_telegram(text, send=send)
        results.append(row)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["synthetic", "aws"], default="synthetic")
    parser.add_argument("--model", choices=MODELS, default="baseline")
    parser.add_argument("--send", action="store_true", help="Invia davvero a Telegram")
    args = parser.parse_args()
    if args.mode == "synthetic":
        raw, _ = genera_costi()
        as_of = pd.Timestamp(END_DATE)+pd.Timedelta(days=2)
    else:
        raw, as_of = scarica_costi_aws(), pd.Timestamp.now().normalize()
    print(json.dumps(run_daily(raw, as_of=as_of, model=args.model, send=args.send), default=str, indent=2))


if __name__ == "__main__":
    main()
