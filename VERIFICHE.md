# Verifiche eseguite e limiti

Lavoro verificato nel Docker Linux locale il 27–28 ottobre 2026, Python 3.11.18, CPU. I controlli locali non attestano funzionamento su account esterni o deployment pubblico.

## Test finali

- Sorgenti finali in `aheadlab-test`, `RUN_MODEL_TESTS=1 pytest -q`: **CloudGuard 60, StockSense 70, SolarCast 55 test passati** (185 totali).
- Build standalone via Docker Compose: tre immagini costruite, senza import o dipendenze tra i progetti.
- Runner `scripts/test_all.py --models`: **185 test passati anche nelle immagini finali**, non-root, cache Hugging Face condivisa scrivibile. Restano warning non bloccanti su alias calendario pandas deprecati.
- `scripts/test_dashboards.py --models`: navigazione delle tre dashboard con Timestral reale; SolarCast verificato sia A sia B. AppTest, non browser visuale.
- `docker compose up --no-build`: tre servizi avviati; `/_stcore/health` su localhost 8501, 8502, 8503 → **HTTP 200, ok**.
- Spec graph validato; nessun dato grezzo, peso, cache Python o `.env` reale incluso nei file esportabili.

Sono stati aggiunti test di regressione per dati AWS provvisori senza gruppi, selezione servizi prima del target, calendari di valutazione invertiti/duplicati/incompleti, invalidazione della cache dashboard al cambio Excel, e copia degli array NumPy read-only prima del passaggio a PyTorch. Nessun test rimosso per ottenere il verde.

## Esportazione indipendente

`scripts/export_repos.py` provato in una cartella temporanea esterna: 153 file esportati, senza Excel, pesi o `.env` reale. Test eseguiti montando **un solo repository per container**, senza accesso alle altre cartelle: CloudGuard 58 passati + 2 integrazioni saltate, StockSense 68 + 2, SolarCast 53 + 2. Dimostra che non dipendono dal workspace padre.

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
- Nessun deploy pubblico, repo remoto, sito GitHub Pages o screenshot di browser.
- CloudGuard non recupera automaticamente giorni saltati perché provvisori e non deduplica gli invii: serve uno stato persistente per produzione.
- SolarCast operativo richiede storico recente fornito dall'utilizzatore. Il modello non trasforma PVGIS storico in misure attuali.
- Nessuna garanzia commerciale o di calibrazione dei quantili aggregati.
