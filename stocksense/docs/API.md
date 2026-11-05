# StockSense HTTP API

API locale senza autenticazione, solo localhost. Non invia ordini e non scarica UCI automaticamente.

- `GET /api/health`: `{status,app}`.
- `GET /api/meta`: modelli, sorgenti, default e `uci_available`.
- `POST /api/forecast`: `source` synthetic/uci; `model` moving_average/seasonal_naive/auto_ets/5M/28M/209M; `top_n` 1–50; `overrides` booleano; `lead_time` 1–90, `cycle` 1–30, `min_lot` 1–10000, `level` p90/p99/mediana.
- Con overrides=false si usa `config/prodotti.csv`; con true i parametri richiesti si applicano a tutti gli SKU. Orizzonte almeno max(30, lead+ciclo).
- Risposta: `app,source,model,as_of,metrics,orders,products,metadata`.
- `orders`: sku, description, order_date, arrival_date e campi di `calcola_riordino` (da_ordinare, urgenza, giacenza, giorni_copertura, domanda_prevista, scorta_sicurezza, politica, in_arrivo).
- `products`: sku, description, params, history `{time,value}` e forecast `{time,median,stock,lower?,upper?}`. Stock è proiezione senza nuovi arrivi. Bande solo per Timestral.
- `GET /api/reports`: `{reports:[{id,label,metadata}]}`.
- `GET /api/reports/{id}`: `{id,metadata,tables}` con array di righe CSV; il registro inventario_giornaliero non viene caricato via HTTP. Percorsi arbitrari non ammessi.

Il file UCI è locale in `data/raw/online_retail_II.xlsx`; hash della sorgente invalida la cache. Inventario sempre simulato nelle risposte web. Nessun riordino è un'azione esterna: il CSV viene costruito dal frontend sui risultati scelti.

Errori JSON detail: 422 validazione, 400 dati incompatibili, 409 calcolo concorrente, 503 sorgente/modello assente, 404 risorsa sconosciuta. Un calcolo per processo; annullare fetch non interrompe inferenza server. JSON non finiti diventano null. OpenAPI `/docs` e `/openapi.json`. Frontend servito da `web/dist` sulla stessa origine.
