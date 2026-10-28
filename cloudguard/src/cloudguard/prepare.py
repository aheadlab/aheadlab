import numpy as np
import pandas as pd


def valida_dati(df):
    required = {"data", "servizio", "costo", "valuta", "estimated"}
    if not required.issubset(df.columns):
        raise ValueError(f"Colonne richieste: {sorted(required)}")
    out = df.copy()
    out["data"] = pd.to_datetime(out.data, errors="raise")
    if out.data.isna().any() or out.data.dt.tz is not None or (out.data != out.data.dt.normalize()).any():
        raise ValueError("Date giornaliere senza timezone richieste")
    out["costo"] = pd.to_numeric(out.costo, errors="raise")
    if not np.isfinite(out.costo).all():
        raise ValueError("Costi non finiti")
    if out[["servizio", "valuta"]].isna().any().any() or (out.valuta == "").any():
        raise ValueError("Servizio e valuta obbligatori")
    if not out.estimated.map(lambda x: isinstance(x, (bool, np.bool_))).all():
        raise ValueError("estimated deve essere booleano")
    if out.valuta.nunique() > 1:
        raise ValueError("Selezionare una sola valuta prima di aggregare")
    return out


def tabella_giornaliera(df, min_giorni=60, selection_end=None):
    if not isinstance(min_giorni, int) or min_giorni < 1:
        raise ValueError("min_giorni positivo richiesto")
    df = valida_dati(df)
    if df.empty:
        return pd.DataFrame(index=pd.DatetimeIndex([], name="data"))
    piv = df.pivot_table(index="data", columns="servizio", values="costo", aggfunc="sum")
    reported = pd.DatetimeIndex(df.attrs.get('reported_dates', []))
    dates = piv.index.union(reported)
    piv = piv.reindex(pd.date_range(dates.min(), dates.max(), freq='D')).fillna(0.)
    training = piv if selection_end is None else piv.loc[:pd.Timestamp(selection_end)]
    piv = piv.loc[:, ((training > 0).sum() >= min_giorni) & (training.sum() >= 1)]
    piv.attrs["valuta"] = df.valuta.iloc[0]
    provisional = set(df.loc[df.estimated, 'data']) | set(df.attrs.get('estimated_dates', []))
    piv.attrs["provisional_dates"] = sorted(provisional)
    return piv


def valida_serie(serie):
    if not isinstance(serie, pd.Series) or not isinstance(serie.index, pd.DatetimeIndex) or serie.empty:
        raise ValueError("Serie giornaliera non vuota richiesta")
    if serie.index.tz is not None or serie.index.has_duplicates or not serie.index.is_monotonic_increasing:
        raise ValueError("Indice ordinato, unico, senza timezone richiesto")
    if not serie.index.equals(pd.date_range(serie.index[0], periods=len(serie), freq="D")):
        raise ValueError("Calendario giornaliero completo richiesto")
    if not np.isfinite(serie.to_numpy(dtype=float)).all():
        raise ValueError("Serie non finita")
    return serie
