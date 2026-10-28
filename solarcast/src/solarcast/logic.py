"""Half-open contiguous blocks, elapsed duration and single capacity scaling."""
import numpy as np
import pandas as pd
from .prepare import validate_index


def fasce_migliori(prev_mediana, prev_p10, ore_utc, kwp, soglia_kw=None, durata_min_ore=2):
    validate_index(ore_utc)
    threshold = .4*kwp if soglia_kw is None else soglia_kw
    if not all(np.isfinite([kwp, threshold, durata_min_ore])) or kwp <= 0 or threshold < 0 or durata_min_ore <= 0:
        raise ValueError('Invalid capacity, threshold or duration')
    median = np.asarray(prev_mediana, dtype=float)
    lower = median if prev_p10 is None else np.asarray(prev_p10, dtype=float)
    if median.shape != (len(ore_utc),) or lower.shape != median.shape:
        raise ValueError('Forecast lengths must match timestamps')
    above = np.isfinite(lower) & np.isfinite(median) & (lower*kwp >= threshold)
    blocks, start = [], None
    for i, good in enumerate(np.r_[above, False]):
        if good and start is None:
            start = i
        elif not good and start is not None:
            if i-start >= durata_min_ore:
                end = ore_utc[i-1]+pd.Timedelta(hours=1)
                blocks.append(dict(start=ore_utc[start].tz_convert('Europe/Rome'),
                    end=end.tz_convert('Europe/Rome'), hours=i-start,
                    expected_kwh=float(median[start:i].sum()*kwp),
                    basis='p10' if prev_p10 is not None else 'median_indicative'))
            start = None
    return blocks
