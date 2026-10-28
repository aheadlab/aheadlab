"""Per-SKU supplier assumptions with an explicit default row."""
from pathlib import Path
import pandas as pd
from .baselines import _integer

DEFAULT = dict(lead_time=14, ciclo=7, lotto_minimo=1, livello='p90')


def load_config(path=Path('config/prodotti.csv')):
    frame = pd.read_csv(path, dtype={'sku': str})
    if frame.sku.duplicated().any():
        raise ValueError('Duplicate SKU configuration')
    result = {}
    for row in frame.itertuples(index=False):
        values = {}
        for source, target in [('lead_time_giorni', 'lead_time'),
                               ('ciclo_riordino_giorni', 'ciclo'), ('lotto_minimo', 'lotto_minimo')]:
            value = float(getattr(row, source))
            if not value.is_integer():
                raise ValueError(f'{source} must be integer')
            values[target] = _integer(int(value), target)
        levels = {.5: 'mediana', .9: 'p90', .99: 'p99'}
        if row.livello_servizio not in levels:
            raise ValueError('Supported service levels: 0.5, 0.9, 0.99')
        values['livello'] = levels[row.livello_servizio]
        result[row.sku] = values
    return result


def for_sku(config, sku):
    return config.get(str(sku), config.get('*', DEFAULT)).copy()
