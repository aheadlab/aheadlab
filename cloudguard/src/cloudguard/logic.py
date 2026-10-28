import numpy as np
import pandas as pd
from .baselines import seasonal_naive
from .forecaster import prevedi
from .prepare import valida_serie

MODELS = ("baseline", "5M", "28M", "123M", "209M")


def forecast(history, h, model="baseline"):
    if model not in MODELS:
        raise ValueError("Modello sconosciuto")
    return seasonal_naive(history, h) if model == "baseline" else prevedi(history, h, taglia=model)


def stima_fine_mese(serie, taglia="baseline", *, predictor=None):
    serie = valida_serie(serie)
    today = serie.index[-1]
    h = (today + pd.offsets.MonthEnd(0) - today).days
    spent = float(serie[serie.index.to_period("M") == today.to_period("M")].sum())
    result = dict(speso=spent, stima=spent, basso=None, alto=None, giorni_mancanti=h)
    if h == 0:
        result.update(basso=spent, alto=spent)
        return result
    p = (predictor or (lambda y, h: forecast(y, h, taglia)))(serie.to_numpy(), h)
    result["stima"] += float(np.asarray(getattr(p, "mediana", p)).sum())
    if hasattr(p, "p10"):
        result.update(basso=spent+float(p.p10.sum()), alto=spent+float(p.p90.sum()))
    return result


def controlla_giorno(serie, taglia="baseline", *, minimo=5., as_of=None,
                     provisional_dates=(), predictor=None):
    serie = valida_serie(serie)
    if not np.isfinite(minimo) or minimo < 0:
        raise ValueError("minimo deve essere finito e non negativo")
    day = serie.index[-1]
    now = pd.Timestamp(as_of if as_of is not None else pd.Timestamp.now()).normalize()
    provisional = set(pd.to_datetime(provisional_dates))
    if day > now-pd.Timedelta(days=2) or any(d in provisional for d in serie.index):
        return dict(data=day, valutato=False, anomalia=False, motivo="dati recenti/provvisori")
    if len(serie) < 29:
        return dict(data=day, valutato=False, anomalia=False, motivo="storico insufficiente")
    history, real = serie.to_numpy()[:-1], float(serie.iloc[-1])
    if taglia == "baseline" and predictor is None:
        expected = float(history[-28:].mean())
        upper = expected + 3*float(history[-28:].std())
    else:
        p = (predictor or (lambda y, h: forecast(y, h, taglia)))(history, 1)
        expected, upper = float(p.mediana[0]), float(p.p99[0])
    return dict(data=day, valutato=True, reale=real, atteso=expected, soglia=upper,
                anomalia=bool(real > upper and real-expected >= minimo))
