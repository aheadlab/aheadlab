"""Temporal prefix-only evaluation; event denominators use evaluated dates."""
import numpy as np
import pandas as pd
from .baselines import seasonal_naive, moving_average
from .metrics import mae, mase, coverage
from .logic import forecast, controlla_giorno
from .prepare import valida_serie


def benchmark_forecast(table, model="baseline", folds=20, step=7, horizons=(7, 30), predictor=None):
    if folds < 1 or step < 1 or any(h < 1 for h in horizons):
        raise ValueError("Parametri rolling positivi richiesti")
    methods = {"seasonal_naive": seasonal_naive, "moving_average": moving_average}
    if model != "baseline" or predictor is not None:
        methods[model] = predictor or (lambda y, h: forecast(y, h, model))
    rows = []
    for service in table:
        series = valida_serie(table[service])
        for h in horizons:
            for fold in range(folds):
                end = len(series)-h-fold*step
                if end < 60:
                    raise ValueError("Storico insufficiente per tutti i tagli richiesti")
                history, actual = series.iloc[:end].to_numpy(), series.iloc[end:end+h].to_numpy()
                for name, method in methods.items():
                    p = method(history.copy(), h)
                    median = getattr(p, "mediana", p)
                    rows.append(dict(servizio=service, modello=name, h=h, fold=fold,
                                     origine=series.index[end-1], mae=mae(actual, median),
                                     mase=mase(actual, median, history, m=7),
                                     coverage80=coverage(actual, p.p10, p.p90) if hasattr(p, "p10") else np.nan))
    return pd.DataFrame(rows)


def anomaly_metrics(evaluated, events):
    """Only evaluated service/date pairs count, including partially intersecting events."""
    required = {"servizio", "data", "anomalia"}
    if not required.issubset(evaluated.columns):
        raise ValueError("Colonne valutazione mancanti")
    if evaluated.duplicated(["servizio", "data"]).any():
        raise ValueError("Giorni valutati duplicati")
    truth, detected, eligible = set(), 0, 0
    days = {(r.servizio, pd.Timestamp(r.data)) for r in evaluated.itertuples()}
    alerts = {(r.servizio, pd.Timestamp(r.data)) for r in evaluated.itertuples() if r.anomalia}
    for event in events.itertuples():
        event_days = {(event.servizio, d) for d in pd.date_range(event.inizio, periods=event.giorni)} & days
        if event_days:
            eligible += 1
            detected += bool(event_days & alerts)
            truth |= event_days
    tp, fp = len(alerts & truth), len(alerts-truth)
    return dict(giorni_valutati=len(days), giorni_anomali=len(truth), veri_positivi=tp,
                falsi_allarmi=fp, precisione=tp/len(alerts) if alerts else np.nan,
                recall_giorni=tp/len(truth) if truth else np.nan,
                eventi_valutati=eligible, eventi_trovati=detected,
                recall_eventi=detected/eligible if eligible else np.nan)


def benchmark_anomalies(table, events, model="baseline", days=300, predictor=None):
    if days < 1:
        raise ValueError("days positivo richiesto")
    methods = ["baseline"] + ([model] if model != "baseline" or predictor else [])
    summaries, details = [], []
    for method in methods:
        rows = []
        for service in table:
            series = valida_serie(table[service])
            for i in range(max(28, len(series)-days), len(series)):
                result = controlla_giorno(series.iloc[:i+1], method,
                                         as_of=series.index[i]+pd.Timedelta(days=2),
                                         provisional_dates=table.attrs.get("provisional_dates", ()),
                                         predictor=predictor if method != "baseline" else None)
                if result["valutato"]:
                    rows.append(dict(servizio=service, **result))
        evaluated = pd.DataFrame(rows, columns=["servizio", "data", "valutato", "reale", "atteso", "soglia", "anomalia"])
        summaries.append(dict(modello="mean_3sigma" if method == "baseline" else method,
                              **anomaly_metrics(evaluated, events)))
        evaluated["modello"] = summaries[-1]["modello"]
        details.append(evaluated)
    return pd.DataFrame(summaries), pd.concat(details, ignore_index=True)
