# aheadlab — tre progetti pronti in locale

Tre applicazioni autonome di previsione su CPU, realizzate a partire da [`PROGETTI.md`](PROGETTI.md). Ogni cartella ha package Python, frontend React/TypeScript, API FastAPI, Dockerfile, test, workflow standalone, licenza e risultati riproducibili. Non ci sono import fra i progetti.

| Progetto | Applicazione | Dashboard locale |
|---|---|---|
| [CloudGuard](cloudguard/README.md) | Costi cloud, stima mensile, anomalie | http://localhost:8501 |
| [StockSense](stocksense/README.md) | Vendite, riordini CSV e simulazione scorte | http://localhost:8502 |
| [SolarCast](solarcast/README.md) | Fotovoltaico, meteo e fasce di autoconsumo | http://localhost:8503 |

## Documentazione per sottoprogetto

Ogni progetto mantiene una guida autonoma, esportabile insieme al codice:

- [CloudGuard — operazioni e API](cloudguard/docs/OPERATIONS.md): demo, schema costi, AWS/Telegram opt-in, report, diagnosi e Docker.
- [StockSense — operazioni e API](stocksense/docs/OPERATIONS.md): dati UCI/cache, configurazione SKU, riordini, simulazione, report e Docker.
- [SolarCast — operazioni e API](solarcast/docs/OPERATIONS.md): modalità retrospettiva/operativa, unità UTC/kWp, covariate, fasce, notifiche e Docker.

Le interfacce offrono navigazione responsive, tema chiaro/scuro, filtri persistenti, grafici interattivi ed esportazione CSV. CloudGuard separa servizi e anomalie; StockSense include selezione multipla dei riordini e schede SKU; SolarCast mostra dettaglio orario e agenda delle fasce. Nessuna delle UI invia ordini o notifiche.

Ogni `docs/API.md` descrive il contratto HTTP; `/docs` sul servizio espone OpenAPI. I singoli `README.md` riassumono il prodotto e i risultati misurati; `SPEC.md` conserva i contratti; `docs/OPERATIONS.md` spiega come usarlo e diagnosticare i problemi. Il registro trasversale delle verifiche rimane in [VERIFICHE.md](VERIFICHE.md).

## Avvio dei tre progetti

Da questa cartella, con Docker Desktop/Engine attivo:

```bash
docker compose up --build
```

Lasciare il comando aperto; le tre applicazioni partono in modalità demo senza credenziali. Le porte sono esposte solo su localhost. `Ctrl+C` arresta i servizi; `docker compose down` rimuove container e rete del progetto, non la cache dei modelli.

Il primo build installa PyTorch CPU e Timestral ufficiale. I pesi si scaricano quando si seleziona un modello, nella cache Docker condivisa; niente download o uso di account AWS nelle demo. Per un build solo baseline si può impostare `INSTALL_MODEL=false` prima del comando. Ogni cartella può anche essere costruita ed eseguita da sola: vedere il rispettivo README.

## Test ripetibili

Con Python sul computer host (serve solo la libreria standard):

```bash
python scripts/test_all.py --build --models
python scripts/test_dashboards.py --models
```

Prima dei test browser avviare i servizi con `docker compose up -d --wait`. Il runner browser usa un container Playwright: non richiede Node sul computer host.

**Suite attuale: 200 test Python passati**, inclusa inferenza reale 5M: CloudGuard 65, StockSense 75, SolarCast 60. **9 test Chromium** coprono desktop/mobile, filtri, esportazione, errori recuperabili, tema e consenso ai dati pubblici; `--models` aggiunge tre chiamate HTTP con Timestral 5M reale, SolarCast B incluso. Senza `--models`, due integrazioni Python per progetto vengono saltate. I benchmark 28M/209M esistenti restano invariati.

## Risultati, senza promesse gonfiate

- **CloudGuard, sintetico, protocollo completo:** MAE a 30 giorni 1,749 USD con 5M contro 2,227 USD della baseline settimanale. Il recall dei giorni anomali è però **50% contro 95,45%** della regola classica, pur trovando entrambi tutti i 10 eventi nel periodo valutato.
- **StockSense, UCI reale:** benchmark completi su 50 SKU, 8 origini e simulazione 180 giorni per 5M, 28M e 209M. MAE medio rispettivamente 41,318 / 40,995 / 40,528 pezzi contro 49,692 di AutoETS. Le politiche Timestral riducono gli stockout **aumentando molto la giacenza**; l'inventario è simulato, non osservato. MASE geometrico spesso zero per singoli casi perfetti: non è evidenza di perfezione generale.
- **SolarCast, PVGIS:** 364 origini nel 2023, orizzonte 48 ore. MAE energia giornaliera 0,565 kWh/kWp per 5M + meteo contro **0,544 della regressione**. Il meteo futuro usato è osservato: risultato oracle ottimistico, non operativo. PVGIS è simulato, non misurato.

CSV, grafici SVG e protocolli sono nei rispettivi `results/`. Lo smoke 209M StockSense e lo smoke 28M SolarCast sono separati dai benchmark completi. Dettagli delle verifiche e dei limiti in [`VERIFICHE.md`](VERIFICHE.md).

## Separare i repository

Le directory sono già autonome. Per esportarle senza dataset ignorati, cache, ambiente virtuale e `.env` locale:

```bash
python scripts/export_repos.py --output ../aheadlab-export
```

La directory destinazione deve essere nuova ed esterna a questa workspace. Lo script include file versionati e nuovi non ignorati; non copia la storia Git, non inizializza repository e non crea nulla su GitHub. In seguito si potrà inizializzare ciascuna cartella esportata e collegarla ai repository `aheadlab/cloudguard`, `aheadlab/stocksense`, `aheadlab/solarcast`. I workflow `.github/workflows/` di ciascun progetto si attivano quando quella cartella diventa radice di un repository.

## Cosa non è stato fatto

- Nessun repository remoto creato, nessun deploy pubblico né sito GitHub Pages.
- AWS Cost Explorer e Telegram implementati e testati con stub/dry-run, **non con credenziali reali**. Nessuna chiamata AWS fatturabile o messaggio inviato.
- CloudGuard non ha recupero persistente dei giorni provvisori né deduplicazione degli invii: non è ancora un monitoraggio di produzione.
- Shopify e integrazioni inverter non implementati; erano opzionali. SolarCast operativo richiede produzione recente fornita dall'utilizzatore, non può prevedere oggi da uno storico PVGIS vecchio di anni.
- Nessuna demo online. I test browser producono screenshot locali in `<progetto>/web/test-results/`, esclusi da Git; i grafici versionati restano quelli dei benchmark.
- Le API sono workspace locali senza autenticazione: non esporle su Internet. Il limite di un calcolo contemporaneo vale per processo; usare un solo worker. Le preferenze salvate nel browser possono riattivare il modello precedentemente scelto.

## Contratti e licenze

Specifiche sintetiche: [`goal-and-requirements.md`](goal-and-requirements.md), [`architecture.md`](architecture.md) e `SPEC.md` in ogni prodotto. Restano draft per la revisione dell'utente. Il brief originale non viene riscritto come se tutte le sue checklist esterne fossero completate.

Codice dei tre progetti MIT. Timestral libreria Apache 2.0, pesi MIT modificata Mistral con restrizione sul fatturato consolidato **mensile** oltre 20 milioni USD nel mese precedente: leggere la licenza ufficiale prima dell'uso commerciale. Dataset UCI CC BY 4.0; PVGIS © European Union; meteo Open-Meteo con attribuzione e condizioni del servizio gratuito non commerciale. Pesi e dati grezzi non sono versionati.
