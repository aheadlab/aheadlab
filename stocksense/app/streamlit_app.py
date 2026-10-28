"""Three-page local application; no automatic UCI or weights downloads."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from stocksense.demo import synthetic_transactions, simulated_stock
from stocksense.ingest import converti_una_volta, source_fingerprint
from stocksense.prepare import pulisci, vendite_giornaliere
from stocksense.forecast_all import forecast, MODELS
from stocksense.config import load_config, for_sku
from stocksense.logic import calcola_riordino

st.set_page_config(page_title='StockSense', layout='wide')
st.title('StockSense — vendite e riordini')
st.warning('Giacenze SIMULATE (seed 42), non rilevate in magazzino. Le vendite osservate non identificano la domanda persa negli stockout storici.')
page = st.sidebar.radio('Pagina', ['Da fare oggi', 'Prodotto', 'Risultati'])
source = st.sidebar.selectbox('Dati', ['synthetic', 'uci'])
model = st.sidebar.selectbox('Modello (Timestral richiede pesi opzionali)', MODELS)
config = load_config()
default = for_sku(config, '*')
override = st.sidebar.checkbox('Modifica parametri per tutti gli SKU')
lead = st.sidebar.number_input('Lead time', 1, 90, default['lead_time'])
cycle = st.sidebar.number_input('Ciclo', 1, 30, default['ciclo'])
level = st.sidebar.selectbox('Livello euristico', ['p90', 'p99', 'mediana'])
st.sidebar.caption('Baseline: previsione puntuale senza banda né scorta quantile. Somme di quantili: nessun livello di servizio garantito.')

@st.cache_data
def data(source, fingerprint):
    clean = pulisci(synthetic_transactions(products=50) if source == 'synthetic' else converti_una_volta())
    # Fixed training-only universe, compatible with full CLI evaluation.
    cutoff = clean.giorno.max()-pd.Timedelta(days=239)
    daily = vendite_giornaliere(clean, 50, cutoff)
    descriptions = clean.drop_duplicates('StockCode').set_index('StockCode').Description.to_dict()
    return daily, descriptions

@st.cache_data
def predictions(daily, model, horizon):
    return {sku: forecast(daily[sku].to_numpy(), horizon, model) for sku in daily}

if page == 'Risultati':
    folder = Path(st.text_input('Cartella risultati', 'results/smoke-baseline'))
    if (folder/'metadata.json').exists():
        meta = json.loads((folder/'metadata.json').read_text())
        st.info(f"Dati: {meta['data']} — esecuzione: {meta['mode']} — INVENTARIO SIMULATO")
        st.json(meta)
        for name in ['riepilogo', 'simulazione']:
            st.subheader(name)
            st.dataframe(pd.read_csv(folder/f'{name}.csv'), hide_index=True)
    else:
        st.info('Eseguire scripts/run_backtest.py per produrre risultati; nessun benchmark viene inventato.')
    st.stop()
try:
    fingerprint = source_fingerprint() if source == 'uci' else 'synthetic-v1'
    daily, descriptions = data(source, fingerprint)
    params = {sku: (dict(for_sku(config, sku), lead_time=int(lead), ciclo=int(cycle), livello=level)
                    if override else for_sku(config, sku)) for sku in daily}
    horizon = max(30, max(p['lead_time']+p['ciclo'] for p in params.values()))
    preds = predictions(daily, model, horizon)
except Exception as exc:
    st.error(f'Caricamento/previsione fallita, nessun fallback: {exc}')
    st.stop()
stock = simulated_stock(daily)
asof = daily.index[-1]+pd.Timedelta(days=1)
rows = []
for sku in daily:
    rows.append(dict(sku=sku, descrizione=descriptions.get(sku, ''), data_ordine=asof,
                     arrivo_previsto=asof+pd.Timedelta(days=params[sku]['lead_time']),
                     **calcola_riordino(preds[sku], stock[sku], **params[sku])))
orders = pd.DataFrame(rows)
st.caption(f'Dati: {source}; decisioni al {asof.date()} (non oggi); arrivi iniziali ipotizzati nulli.')
if page == 'Da fare oggi':
    orders['priorita'] = orders.urgenza.map({'URGENTE': 0, 'DA ORDINARE': 1, 'OK': 2})
    orders = orders.sort_values(['priorita', 'sku']).drop(columns='priorita')
    colors = {'URGENTE': '#f6b5b5', 'DA ORDINARE': '#ffe7a0', 'OK': '#bde7c2'}
    st.dataframe(orders.style.map(lambda x: f'background-color: {colors[x]}', subset=['urgenza']), hide_index=True)
    actionable = orders[orders.da_ordinare > 0]
    st.download_button('Scarica CSV ordine', actionable.to_csv(index=False).encode('utf-8'), 'ordini.csv', 'text/csv')
else:
    sku = st.selectbox('Prodotto', list(daily), format_func=lambda s: f'{s} — {descriptions.get(s, "")}')
    pred = preds[sku]
    dates = pd.date_range(asof, periods=horizon)
    fig = go.Figure(go.Scatter(x=daily.index[-120:], y=daily[sku].iloc[-120:], name='Vendite grezze'))
    if hasattr(pred, 'p10'):
        fig.add_trace(go.Scatter(x=dates, y=pred.p10, name='p10', line=dict(width=0)))
        fig.add_trace(go.Scatter(x=dates, y=pred.p90, name='p90', fill='tonexty', line=dict(width=0)))
    fig.add_trace(go.Scatter(x=dates, y=pred.mediana, name='Previsione'))
    st.plotly_chart(fig, width='stretch')
    st.line_chart(pd.DataFrame({'Giacenza simulata senza nuovi arrivi': np.maximum(stock[sku]-np.cumsum(pred.mediana), 0)}, index=dates))
    st.dataframe(orders[orders.sku == sku], hide_index=True)
