"""UTC is the storage contract; missing hours are never zero production."""
import pandas as pd


def validate_index(index, contiguous=True):
    if not isinstance(index, pd.DatetimeIndex) or str(index.tz) != 'UTC':
        raise ValueError('Expected timezone-aware UTC timestamps')
    if index.empty or index.has_duplicates or not index.is_monotonic_increasing:
        raise ValueError('Timestamps must be nonempty, unique and ordered')
    if not index.equals(index.floor('h')):
        raise ValueError('Timestamps must be hourly boundaries')
    if contiguous and len(index) > 1 and not (index.diff()[1:] == pd.Timedelta(hours=1)).all():
        raise ValueError('Timestamps must be contiguous hourly UTC')


def unisci(produzione, meteo):
    validate_index(produzione.index, False)
    validate_index(meteo.index, False)
    return produzione.join(meteo, how='left').asfreq('h')
