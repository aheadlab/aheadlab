"""Streamlit UI defaults to an offline, synthetic retrospective."""
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from solarcast.demo import synthetic
from solarcast.ingest import historical_dataset
from solarcast.forecast import forecast
from solarcast.logic import fasce_migliori

st.set_page_config(page_title='SolarCast', layout='wide')
st.title('☀️ SolarCast')
st.caption('Produzione normalizzata; Europe/Rome solo per visualizzazione. Nessuna previsione attuale inventata.')
page = st.sidebar.radio('Pagina', ['Demo retrospettiva', 'PVGIS storico (oracle)', 'Risultati'])
lat = st.sidebar.number_input('Latitudine', -90., 90., 45.82)
lon = st.sidebar.number_input('Longitudine', -180., 180., 8.83)
kwp = st.sidebar.number_input('Potenza kWp', .1, 10000., 6.)
angle = st.sidebar.slider('Inclinazione', 0, 90, 30)
aspect = st.sidebar.slider('Orientamento (0=sud)', -180, 180, 0)
model = st.sidebar.selectbox('Modello', ['baseline', '5M', '28M', '209M'])
method = st.sidebar.selectbox('Metodo', ['seasonal_naive24', 'radiation_regression'] if model == 'baseline' else ['A', 'B', 'seasonal_naive24', 'radiation_regression'])
context = st.sidebar.number_input('Contesto massimo (ore)', 24, 32768, 720)


@st.cache_data
def demo_data():
    return synthetic()


@st.cache_data
def pv_data(lat, lon, year, angle, aspect):
    return historical_dataset(lat, lon, year, angle, aspect)


@st.cache_data
def prediction(history, future, method, model, context):
    return forecast(history, future, method, '5M' if model == 'baseline' else model, context)


if page == 'Risultati':
    st.info('Smoke sintetico ≠ benchmark annuale; B/C con meteo osservato sono oracle.')
    reports = sorted(Path('results').glob('*/summary.csv'))
    if not reports:
        st.write('Nessun risultato disponibile. Eseguire scripts/run_backtest.py.')
    else:
        report = st.selectbox('Report disponibile', reports, format_func=str)
        st.dataframe(pd.read_csv(report))
        st.code(report.with_name('metadata.json').read_text(encoding='utf-8'), language='json')
    st.stop()

if page.startswith('PVGIS'):
    st.warning('PVGIS è produzione simulata storica, non misurata. Meteo futuro osservato = oracle ottimistico.')
    year = st.sidebar.number_input('Anno storico', 2005, 2023, 2023)
    if not st.checkbox('Scarica/usa cache PVGIS e meteo storico (rete esplicita)'):
        st.stop()
    try:
        data = pv_data(lat, lon, year, angle, aspect)
    except Exception as exc:
        st.error(str(exc))
        st.stop()
else:
    st.info('Demo sintetica retrospettiva deterministica: geometria/località non modificano la simulazione. Baseline senza rete.')
    data = demo_data()

origin = pd.Timestamp(st.date_input('Origine retrospettiva UTC', data.index[-1].date()-pd.Timedelta(days=2),
    min_value=data.index[0].date()+pd.Timedelta(days=30), max_value=data.index[-1].date()-pd.Timedelta(days=1)), tz='UTC')
history = data.loc[data.index < origin]
future = data.loc[origin:origin+pd.Timedelta(hours=47)]
try:
    p = prediction(history, future.drop(columns='kwh'), method, model, int(context))
except Exception as exc:
    st.error(str(exc))
    st.stop()
st.json(p.metadata)
frame = p.frame
x = frame.index.tz_convert('Europe/Rome')
fig = make_subplots(specs=[[{'secondary_y': True}]])
if 'p10' in frame:
    fig.add_trace(go.Scatter(x=x, y=frame.p90*kwp, line={'width':0}, name='p90'))
    fig.add_trace(go.Scatter(x=x, y=frame.p10*kwp, fill='tonexty', line={'width':0}, name='p10–p90'))
fig.add_trace(go.Scatter(x=x, y=frame['median']*kwp, name='Mediana kWh/ora'))
fig.add_trace(go.Bar(x=x, y=future.shortwave_radiation, opacity=.2, name='Radiazione osservata W/m²'), secondary_y=True)
blocks = fasce_migliori(frame['median'], frame.get('p10'), frame.index, kwp)
for b in blocks:
    fig.add_vrect(x0=b['start'].isoformat(), x1=b['end'].isoformat(), fillcolor='green', opacity=.12, line_width=0)
st.plotly_chart(fig, width='stretch')
st.subheader('Fasce su p10' if 'p10' in frame else 'Fasce indicative sulla mediana — non prudenti')
st.dataframe(pd.DataFrame(blocks))
st.caption('Fine esclusiva; durata trascorsa anche nei cambi DST. Energia attesa dalla mediana, potenza scalata una sola volta. Per uso operativo: API con target misurato recente e meteo contiguo.')
