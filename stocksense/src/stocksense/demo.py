"""Deterministic artificial transactions, NEVER UCI data; simulated stock."""
import numpy as np
import pandas as pd

SEED = 42


def synthetic_transactions(days=730, products=12, seed=SEED):
    rng = np.random.default_rng(seed)
    rows = []
    for day, date in enumerate(pd.date_range('2022-01-01', periods=days)):
        for sku in range(products):
            mean = (3 + sku) * (0.35 if date.dayofweek == 6 else 1) * (1 + .25*np.sin(day*2*np.pi/365))
            quantity = rng.poisson(mean)
            if quantity:
                rows.append((f'DEMO-{day}-{sku}', f'{10000+sku}', f'Prodotto sintetico {sku}', quantity, date, 2.5))
    return pd.DataFrame(rows, columns=['Invoice', 'StockCode', 'Description', 'Quantity', 'InvoiceDate', 'Price'])


def simulated_stock(training, days=21, seed=SEED):
    rng = np.random.default_rng(seed)
    return {sku: float(training[sku].iloc[-days:].sum()*rng.uniform(.3, 2))
            for sku in sorted(training.columns)}
