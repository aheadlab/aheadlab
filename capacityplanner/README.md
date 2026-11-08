# Capacity Planner

Quarto progetto portfolio Aheadlab: una dashboard locale di previsione e
pianificazione della capacità, accompagnata da un esperimento riproducibile.

## Avvio

```powershell
docker compose up -d --build --wait
```

Da questa cartella. UI: **http://localhost:8504**. OpenAPI: `/docs`.
Compose ha un nome progetto proprio, limiti 2 GiB / 1 CPU, bind su loopback;
non modifica i tre servizi Aheadlab precedenti. Il volume esterno dei modelli
si configura con `CAPACITY_MODEL_VOLUME` (nell'ambiente Aheadlab: `aheadlab-hf`).
La demo con baseline funziona senza pesi; Timestral richiede gli snapshot
indicati in `src/capacityplanner/core.py`, scaricabili esplicitamente con
`python scripts/download_models.py --size 5M` (oppure `28M`). La web app non
scarica pesi e non invia comandi all'infrastruttura.

Per un ambiente Docker autonomo, da questa cartella (PowerShell):

```powershell
$env:CAPACITY_MODEL_VOLUME = 'capacityplanner-model-cache'
docker volume create capacityplanner-model-cache
docker compose build
docker run --rm -v capacityplanner-model-cache:/home/app/.cache/huggingface aheadlab-capacityplanner python scripts/download_models.py --size 5M
docker run --rm -v capacityplanner-model-cache:/home/app/.cache/huggingface aheadlab-capacityplanner python scripts/download_models.py --size 28M
docker compose up -d --wait
```

Il download è esplicito; richiede rete solo durante la preparazione. Conservare
la variabile del volume per i successivi comandi Compose. I replay CESNET
inclusi sono consultabili anche senza ricalcolare le previsioni.
Codice, frontend e dipendenze runtime sono tutti locali
al progetto. `Dockerfile.validation` è solo una scorciatoia per l'ambiente
di sviluppo Aheadlab; il Dockerfile principale parte da Python e Node standard.

## Esperienza

- **Pianificazione:** demo sintetica o replay CESNET; scelta modello e serie,
  capacità del modulo, margine, ritardo di attivazione e costo ipotetico.
- **Piano orario:** previsione, osservato, capacità e deficit; esportazione CSV.
- **Ricerca:** risultati sul test finale, modello e baseline scelti in precedenza,
  intervalli statistici e verdetto anche quando il criterio fallisce.
- **Metodo:** origine dei dati e significato delle misure.

I parametri modificati diventano effettivi solo premendo Applica. Errori di
calcolo conservano l'ultimo risultato applicato, con messaggio esplicito.
Preferenze e tema rimangono nel browser. API priva di autenticazione, destinata
al workspace locale su loopback.

## Riprodurre la ricerca

Leggere prima [il protocollo](docs/PROTOCOL.md) e [la matematica](docs/MATHEMATICS.md).

```powershell
python scripts/fetch_data.py
# Ambiente Aheadlab, dalla radice del monorepo:
python capacityplanner/scripts/run_isolated.py inspect
python capacityplanner/scripts/run_isolated.py prepare test benchmark
python capacityplanner/scripts/run_isolated.py analyze
```

Il runner Windows usa un'immagine di validazione separata e dati già locali;
monitoraggio della RAM, rete disabilitata per i benchmark, un job alla volta.
I risultati e il protocollo effettivo vengono scritti in `results/cesnet/`.
I pesi hanno revisioni fissate; i dati sono verificati con SHA-256.

Prima del runner, costruire l'immagine dedicata dalla radice del monorepo:
`docker build -f capacityplanner/Dockerfile.validation -t aheadlab-capacity-validation .`.
La scorciatoia richiede l'immagine locale `aheadlab-stocksense`; non avvia né
modifica il relativo servizio. In un ambiente Python autonomo installare
`pip install -e '.[model,data]'` e, dalla cartella Capacity Planner, eseguire
`python scripts/research.py prepare`, poi `benchmark` e `analyze`.
Il runner isolato è specifico per Windows; il codice di ricerca è portabile.

Il dataset CESNET misura byte di rete: i replay mostrano **Mbit/s medi**. Le
richieste/ora della demo sintetica sono un esempio separato. La conversione
in moduli di capacità è una simulazione e non identifica SKU cloud reali.
Un risultato positivo sul campione non è una garanzia di risparmio in produzione.

## Verifiche

```bash
pytest -q
cd web
npm ci
npm run build
BASE_URL=http://127.0.0.1:8504 npx playwright test
```

Risultati effettivi della sessione: [RESEARCH.md](docs/RESEARCH.md).

La [seconda ricerca](docs/RESEARCH_V2.md) prosegue l'indagine: diagnosi dei
picchi della V1, margini adattivi e protezione reattiva causale, poi confronto
su un nuovo periodo CESNET del 2026. Il [protocollo V2](docs/PROTOCOL_V2.md)
include anche controlli senza AI e conserva la politica originale come
confronto sugli stessi dati nuovi. Non richiede l'avvio della dashboard.
Esperimento concluso: 24 istituzioni, 56 giorni finali, **MAE 28M −35,80%**
rispetto a ETS, ma **capacità +1,20% e deficit 1,540% contro 1,496%**.
Il criterio operativo resta fallito. Suite Python ampliata a **28 test passati**;
diagnosi, confronti delle politiche e misure di tempo/RAM sono nel report V2.
I replay dell'interfaccia rimangono quelli della prima ricerca.

Prima ricerca, su dodici istituzioni CESNET: MAE 28M **−20,79% rispetto a ETS**, ma il piano
non supera il criterio operativo (capacità −6,30%, deficit 2,060% contro
soglia 1%). 19 test Python, tre test Chromium e due inferenze API reali passati.

## Fonti e licenze

Codice MIT. Timestral: libreria Apache 2.0, pesi con propria Modified MIT;
consultare [la licenza dei pesi](https://huggingface.co/mistralai/Timestral-5M/blob/main/LICENSE)
prima dell'uso commerciale. I pesi non sono distribuiti nel repository.

CESNET-TimeSeries24, CC-BY-4.0:
[pubblicazione degli autori](https://doi.org/10.1038/s41597-025-04603-x),
[distribuzione HDF5](https://zenodo.org/records/23296272).
Le trasformazioni effettuate sono conversione dei byte/ora in Mbit/s medi,
selezione di istituzioni sul training e riempimento causale del solo contesto.
