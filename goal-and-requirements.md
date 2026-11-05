---
id: aheadlab-goals
type: goal-and-requirements
title: aheadlab — tre prodotti di previsione
status: draft
---
# aheadlab
Tre prodotti portfolio autonomi, basati sul brief confermato `PROGETTI.md`.

## Overview
CloudGuard prevede costi cloud e segnala anomalie; StockSense traduce previsioni di vendita in riordini; SolarCast prevede energia fotovoltaica e consiglia fasce di autoconsumo. Destinatari: piccoli operatori cloud, negozi e proprietari di impianti, oltre a chi valuta il portfolio.

## Capabilities
- CloudGuard: dati sintetici riproducibili e ingest AWS, previsione mensile, anomalie, Telegram, dashboard e valutazione rolling contro baseline.
- StockSense: ingest Online Retail II, pulizia e serie SKU, previsioni e riordini configurabili, simulazione con lead time, CSV ordini e dashboard.
- SolarCast: ingest PVGIS/Open-Meteo, previsioni a 48 ore con e senza covariate, regressione radiazione, fasce prudenti e dashboard.
- Ogni prodotto ha un workspace web responsive con tema chiaro/scuro, filtri persistenti, grafici interattivi, report navigabili ed esportazione CSV, collegato al proprio backend.
- Ogni prodotto ha test di dominio, API e browser, backtest pubblicabili, limiti espliciti e un avvio Docker indipendente.
- Le interfacce non inviano ordini, notifiche o comandi a dispositivi. Autenticazione multiutente e hosting pubblico sono fuori dal perimetro del workspace locale.

## Success conditions
Le tre cartelle sono esportabili senza import reciproci. I test esercitano pipeline e logica, con test di integrazione distinti per Timestral reale. I risultati riportano fonte dati, modello e protocollo effettivamente eseguito; nessuna promessa di superiorità prima delle misure.

## Technology
Python 3.11, Timestral isolato in forecaster.py, pandas/numpy, FastAPI e React/TypeScript con grafici Recharts; build frontend Node 22 e runtime Docker CPU. Le interfacce sostituiscono integralmente Streamlit secondo la richiesta confermata. Nessun peso, segreto o dataset grezzo in git. Hosting pubblico, creazione repository, account AWS/Telegram e Shopify richiedono servizi esterni e non sono attestabili con soli test locali.
