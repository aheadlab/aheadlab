"""Order-up-to policy; marginal quantile sums are only a heuristic."""
import math
import numpy as np
from .baselines import _integer
from .metrics import _vector


def nonnegative(value, name):
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError(f'{name} must be finite and nonnegative')
    return value


def calcola_riordino(prev, giacenza, in_arrivo=0, lead_time=14, ciclo=7,
                     lotto_minimo=1, livello='p90'):
    lead_time, ciclo = _integer(lead_time, 'lead_time'), _integer(ciclo, 'ciclo')
    lotto_minimo = _integer(lotto_minimo, 'lotto_minimo')
    giacenza = nonnegative(giacenza, 'giacenza')
    in_arrivo = nonnegative(in_arrivo, 'in_arrivo')
    if livello not in ('mediana', 'p90', 'p99'):
        raise ValueError('Supported levels: mediana, p90, p99')
    median = np.maximum(_vector(prev.mediana), 0)
    window = lead_time + ciclo
    if len(median) < window:
        raise ValueError('Forecast horizon must cover lead time plus cycle')
    # Point forecasts deliberately have no quantiles or safety stock.
    probabilistic = hasattr(prev, livello)
    upper = np.maximum(_vector(getattr(prev, livello, median)), 0)
    if upper.shape != median.shape:
        raise ValueError('Forecast shapes must match')
    demand = float(median[:window].sum())
    safety = max(float(upper[:window].sum()) - demand, 0)
    gap = demand + safety - giacenza - in_arrivo
    quantity = max(math.ceil(gap), lotto_minimo) if gap > 0 else 0
    exceeded = np.flatnonzero(np.cumsum(median) > giacenza)
    coverage = int(exceeded[0]) if len(exceeded) else len(median)
    return dict(domanda_prevista=demand, scorta_sicurezza=safety,
                giacenza=giacenza, in_arrivo=in_arrivo, giorni_copertura=coverage,
                da_ordinare=quantity,
                urgenza='URGENTE' if coverage <= lead_time else ('DA ORDINARE' if quantity else 'OK'),
                politica=livello if probabilistic else 'puntuale, senza quantili')
