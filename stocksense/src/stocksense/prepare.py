"""Cleaning and calendar construction; selection is strictly training-only."""
import numpy as np
import pandas as pd

NON_PRODUCTS = {'POST', 'DOT', 'M', 'MANUAL', 'BANK CHARGES', 'AMAZONFEE', 'C2',
                'ADJUST', 'ADJUST2', 'D', 'S', 'PADS', 'CRUK', 'TEST001', 'TEST002'}


def pulisci(frame):
    df = frame.copy()
    df.columns = df.columns.str.strip()
    for alias, canonical in [('InvoiceNo', 'Invoice'), ('UnitPrice', 'Price')]:
        if canonical not in df and alias in df:
            df = df.rename(columns={alias: canonical})
    required = ['Invoice', 'StockCode', 'Quantity', 'Price', 'InvoiceDate']
    if not set(required) <= set(df):
        raise ValueError(f'Required columns: {required}')
    for col in ['Invoice', 'StockCode']:
        df[col] = df[col].astype('string').str.strip().str.upper()
    for col in ['Quantity', 'Price']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df['giorno'] = pd.to_datetime(df.InvoiceDate, errors='coerce').dt.normalize()
    valid = (df.Invoice.notna() & df.Invoice.ne('') & ~df.Invoice.str.startswith('C')
             & df.StockCode.notna() & df.StockCode.ne('') & ~df.StockCode.isin(NON_PRODUCTS)
             & df.giorno.notna() & (df.Quantity > 0) & (df.Price > 0)
             & np.isfinite(df.Quantity) & np.isfinite(df.Price))
    return df.loc[valid].copy()


def vendite_giornaliere(df, top_n=50, cutoff=None):
    if df.empty:
        raise ValueError('No valid transactions')
    if top_n < 1 or cutoff is None:
        raise ValueError('Positive top_n and explicit first test cutoff required')
    training = df[df.giorno < pd.Timestamp(cutoff)]
    totals = training.groupby('StockCode').Quantity.sum().sort_index()
    selected = totals.sort_values(ascending=False, kind='stable').head(top_n).index
    if not len(selected):
        raise ValueError('No training products')
    daily = df.groupby(['giorno', 'StockCode']).Quantity.sum().unstack(fill_value=0)
    calendar = pd.date_range(df.giorno.min(), df.giorno.max(), freq='D')
    return daily.reindex(index=calendar, columns=selected, fill_value=0).astype(float)


def validate_daily(daily):
    if not isinstance(daily, pd.DataFrame) or daily.empty or daily.columns.has_duplicates:
        raise ValueError('Daily data must be nonempty with unique products')
    index = daily.index
    if isinstance(index, pd.DatetimeIndex):
        if (index.hasnans or index.has_duplicates or not index.is_monotonic_increasing
                or not index.equals(index.normalize())
                or not index.equals(pd.date_range(index[0], periods=len(index), freq='D'))):
            raise ValueError('Dates must be unique, increasing, consecutive calendar days')
    elif not isinstance(index, pd.RangeIndex) or index.step != 1:
        raise ValueError('Use daily dates or a unit-step RangeIndex of daily observations')
    if not all(pd.api.types.is_numeric_dtype(dtype) for dtype in daily.dtypes):
        raise ValueError('Daily demand must be numeric')
    values = daily.to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError('Daily demand must be finite and nonnegative')
    return daily


def winsorize_training(history):
    values = np.asarray(history, dtype=float)
    if values.ndim != 1 or not values.size or not np.isfinite(values).all() or (values < 0).any():
        raise ValueError('Training must be finite nonnegative daily observations')
    return np.minimum(values, np.quantile(values, .995))
