# Verifiche eseguite e limiti

Lavoro verificato nel Docker Linux locale, Python 3.11, CPU. I benchmark del 27–28 ottobre 2026 restano invariati; la migrazione web verifica separatamente API, frontend e distribuzione. I controlli locali non attestano funzionamento su account esterni o deployment pubblico.

## Test finali

- `npm run build` nei tre frontend: TypeScript e bundle React compilati con Node 22, senza warning di dimensione chunk.
- Build multistadio via Docker Compose: tre immagini FastAPI/React, senza Streamlit, Node a runtime o dipendenze incrociate.
- `python scripts/test_all.py --models`: **CloudGuard 65, StockSense 75, SolarCast 60 test passati** (200 totali), con modelli reali e utente non-root. Restano warning non bloccanti di deprecazione pandas.
- `python scripts/test_dashboards.py --models`: **9 flussi Chromium passati** su immagini finali, desktop 1440 px/mobile 390 px, più tre richieste HTTP Timestral 5M reali (SolarCast B). Comprendono CSV, filtri, selezione ordini, dettagli, report, recupero da errori e consenso PVGIS. Gli errori di rete sono simulati deliberatamente nei test dedicati.
- Screenshot generati in `web/test-results/` di ciascun progetto, ignorati da Git. CloudGuard desktop e SolarCast mobile controllati visivamente.
- `docker compose up -d --wait --wait-timeout 120`: tre servizi healthy, `/api/health` su localhost 8501/8502/8503 → **HTTP 200**. HTML e asset React serviti dalla stessa API.
- Spec graph validato; nessun dato grezzo, peso, cache Python o `.env` reale incluso nei file esportabili.

Sono stati aggiunti test di regressione per dati AWS provvisori senza gruppi, selezione servizi prima del target, calendari di valutazione invertiti/duplicati/incompleti, invalidazione della cache dashboard al cambio Excel, e copia degli array NumPy read-only prima del passaggio a PyTorch. I test della vecchia UI sono stati sostituiti con test API e browser; la regressione sul cambio Excel rimane coperta via HTTP. Non sono stati disattivati contratti di dominio per ottenere il verde.

## Esportazione indipendente

`scripts/export_repos.py` provato in una cartella esterna: **203 file esportati**, senza Excel, pesi, node_modules, risultati dei test browser o `.env` reale. Ogni cartella esportata è stata costruita con il proprio Dockerfile, senza Timestral: CloudGuard **63 passati + 2 saltati**, StockSense **73 + 2**, SolarCast **58 + 2**. Verificati inoltre HTML/asset compilati, healthcheck, previsioni baseline, errore 503 per modello assente e impossibilità di importare gli altri due progetti.

I workflow standalone includono ora build frontend e Playwright con avvio dell'API. Non sono state avviate esecuzioni GitHub Actions remote; le prove riportate sono locali.

## Timestral reale

Libreria ufficiale fissata al commit `a534bdbd244d64f3d9d743f46c7bf6fc330ed4ff`. Pesi scaricati da Hugging Face nella cache Docker, non nel repository. Snapshot effettivamente usati: 5M `bdd20cfc15a3fea0e4cb5ccef37f8d3ca7aa335f`, 28M `49b26409ac87b5935539a5d8ffe7f397b720db47`, 209M `9874d252ab0aae16f7f7c999f98f98d6ad7d8365`. I loader usano i repository ufficiali; gli snapshot documentano i risultati, non costituiscono un lock automatico di tutte le dipendenze.

- 5M: orizzonti 1 e 14, ordine quantili, batch di due serie e covariate future verificati.
- Output upstream `(1,1,H)` per singola serie, `(2,1,H)` per batch; wrapper `(H,)` anche per H=1.
- 28M e 209M: download e inferenza reale su CPU riusciti; inoltre benchmark StockSense completi.
- Quantili non supportati causano errore, non interpolazione. Il wrapper non sostituisce silenziosamente il modello con una baseline.
- Licenza pesi: soglia di 20 milioni USD di fatturato consolidato **mensile** nel mese precedente; [testo ufficiale](https://huggingface.co/mistralai/Timestral-5M/blob/main/LICENSE).

## CloudGuard

Comandi eseguiti da `cloudguard/`:

```bash
python scripts/run_backtest.py --model baseline
python scripts/run_backtest.py --model 5M --output results/timestral-full
python -m cloudguard.daily
```

Protocollo completo sintetico: seed 7, 400 giorni, cinque servizi, 20 origini per orizzonte 7 e 30, passo 7; 300 giorni di anomalie per servizio. Rigenerato dopo la correzione della selezione servizi sul training; risultati invariati. Metadata include il cutoff di selezione.

- 5M: MAE 1,714 USD a 7 giorni e 1,749 USD a 30; copertura 82%/84%.
- Anomalie: 10/10 eventi valutabili rilevati da entrambi. Su 22 giorni anomali, 5M ne trova 11, regola 3-sigma 21. Nessun falso allarme su questi dati sintetici.
- Daily eseguito senza rete o invii. AWS e Telegram verificati con client simulati.

## StockSense

Dataset ufficiale UCI scaricato: **1.067.371 transazioni**, fogli `Year 2009-2010` e `Year 2010-2011`, 1.037.082 righe dopo pulizia. Periodo 1 dicembre 2009–9 dicembre 2011, ultimo giorno incompleto. Download ufficiale con DOI `10.24432/C5CG6D`; licenza CC BY 4.0 controllata sulla pagina UCI.

```bash
python scripts/run_backtest.py --data uci --model 5M --output results/uci-5M
python scripts/run_backtest.py --data uci --model 28M --output results/uci-28M
python scripts/run_backtest.py --data uci --model 209M --output results/uci-209M
```

Tutti completi: 50 SKU, 8 origini, orizzonte 30, passo 30, simulazione 180 giorni. Tempi osservati nel container di test: circa 271 / 353 / 871 secondi, non benchmark di latenza isolato (altri processi potevano essere attivi).

- MAE medio 5M/28M/209M: 41,318 / 40,995 / 40,528; AutoETS 49,692.
- Con 28M: 81 SKU-giorni stockout, 16.027 pezzi persi, giacenza media 1.878 pezzi; AutoETS 1.040 giorni stockout, 113.417 persi, giacenza media 425. Non è una superiorità gratuita: più scorta e politiche diverse.
- Inventario **simulato**, non misurato. MASE geometrico zero per alcuni modelli a causa di casi perfetti isolati; consultare MAE e distribuzioni per SKU/fold.
- Smoke sintetico e smoke UCI 209M rimangono in cartelle distinte, senza sostituire i report completi.

## SolarCast

```bash
python scripts/run_backtest.py --data pvgis --model 5M --output results/pvgis-5M
python scripts/run_backtest.py --data pvgis --model 28M --quick --output results/pvgis-28M-smoke
python scripts/daily.py
```

Dati pubblici PVGIS v5_3 e Open-Meteo effettivamente scaricati per Varese 2022–2023. Correlazione 2023 tra `P` e radiazione allineati senza shift circa 0,903; uno shift di un'ora cambia il risultato, coerentemente con diverse convenzioni temporali. Non è stato scelto uno shift ottimizzando il test.

5M completo: 364 origini UTC nel 2023, 48 ore, contesto massimo 8.784. MAE energia giornaliera per kWp: A 1,1620; B 0,5647; regressione 0,5440; persistenza 1,3288. **La regressione è migliore di B su questa metrica**, mentre B è migliore sul MAE orario diurno. Meteo osservato futuro = **oracle ottimistico**. Produzione PVGIS simulata, non misure reali. Origini sovrapposte non indipendenti.

28M: solo smoke su quattro origini stagionali con contesto 720, etichettato esplicitamente. Daily è demo retrospettiva dry-run. Test fasce includono cambi DST, fine esclusiva, blocco finale e singola applicazione della potenza nominale.

## Non verificato / non realizzato

- Nessun accesso AWS reale, messaggio Telegram, account Shopify o inverter.
- Nessun deploy pubblico, sito GitHub Pages o repository remoto dedicato ai singoli prodotti. Il monorepo era stato pubblicato prima della migrazione; questa migrazione non è stata inviata con un nuovo push.
- Nessuna autenticazione, isolamento multiutente o validazione per esposizione pubblica delle API locali.
- CloudGuard non recupera automaticamente giorni saltati perché provvisori e non deduplica gli invii: serve uno stato persistente per produzione.
- SolarCast operativo richiede storico recente fornito dall'utilizzatore. Il modello non trasforma PVGIS storico in misure attuali.
- Nessuna garanzia commerciale o di calibrazione dei quantili aggregati.
