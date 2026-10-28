from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from cloudguard.synthetic import genera_costi
from cloudguard.prepare import tabella_giornaliera
from cloudguard.logic import forecast, stima_fine_mese, MODELS
from cloudguard.backtest import benchmark_anomalies

st.set_page_config(page_title="CloudGuard", layout="wide")
st.title("CloudGuard — costi cloud")
st.caption("Demo sintetica riproducibile, USD. Nessuna chiamata AWS o invio Telegram.")
page = st.sidebar.radio("Pagina", ["Previsioni e allarmi", "Risultati"])
if page == "Risultati":
    root = Path(__file__).resolve().parents[1] / "results"
    reports = ([root] if (root / 'metadata.json').exists() else []) + sorted(
        path.parent for path in root.glob('*/metadata.json'))
    if reports:
        preferred = root / 'timestral-full'
        root = st.selectbox('Report', reports, index=reports.index(preferred) if preferred in reports else 0,
                            format_func=lambda path: path.name)
    if (root / "metadata.json").exists():
        st.code((root / "metadata.json").read_text(), language="json")
        for name in ["backtest", "anomalies"]:
            st.subheader(name)
            st.dataframe(pd.read_csv(root / f"{name}.csv"))
    else:
        st.info("Eseguire python scripts/run_backtest.py. Nessun risultato inventato.")
else:
    raw, events = genera_costi()
    table = tabella_giornaliera(raw)
    service = st.sidebar.selectbox("Servizio", table.columns)
    model = st.sidebar.selectbox("Modello (baseline senza download)", MODELS)
    st.sidebar.caption("Timestral richiede installazione model e download esplicito alla selezione; nessun fallback.")
    series = table[service]
    try:
        p = forecast(series.to_numpy(), 30, model)
        dates = pd.date_range(series.index[-1]+pd.Timedelta(days=1), periods=30)
        fig = go.Figure(go.Scatter(x=series.index[-90:], y=series.iloc[-90:], name="Storico"))
        if hasattr(p, "p10"):
            fig.add_trace(go.Scatter(x=dates, y=p.p10, line=dict(width=0), name="p10"))
            fig.add_trace(go.Scatter(x=dates, y=p.p90, fill="tonexty", line=dict(width=0), name="p90"))
        fig.add_trace(go.Scatter(x=dates, y=getattr(p, "mediana", p), name=model))
        st.plotly_chart(fig, width='stretch')
        cutoff = st.slider("Giorni da escludere alla fine (demo mese parziale)", 0, 28, 7)
        month_series = series.iloc[:-cutoff] if cutoff else series
        st.write("Mese riferito al", month_series.index[-1].date())
        st.json(stima_fine_mese(month_series, model))
        st.caption("Somma dei quantili giornalieri: euristica, non intervallo calibrato del totale. Baseline: nessuna banda.")
        _, detail = benchmark_anomalies(table[[service]], events, model, days=30)
        st.subheader("Allarmi ultimi 30 giorni (valutazione retrospettiva)")
        st.dataframe(detail.loc[detail.anomalia])
    except (ValueError, RuntimeError, ImportError, OSError) as error:
        st.error(f"Previsione non disponibile: {error}")
