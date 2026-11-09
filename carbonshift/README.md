# CarbonShift

Quinto progetto portfolio Aheadlab: sceglie quando eseguire un lavoro
elettrico differibile, mantenendo identici durata, energia e scadenza.
Dashboard React/TypeScript, API FastAPI, inferenza Timestral 5M locale e
confronto riproducibile con metodi classici.

**Risultato:** nel test storico separato su sei zone e 176 giorni, emissioni
attribuite **−0,66% rispetto a GBM**, intervallo al 95% [0,12%; 1,20%]. Sono
circa **144 grammi per MWh di lavoro**. Il controllo successivo al rilascio
del modello, di soli 14 giorni, è **inconcludente**. Non è una prova di ROI
o di emissioni marginali realmente evitate. [Ricerca completa](docs/RESEARCH.md).

## Avvio locale

Dalla cartella `carbonshift`, nel workspace Aheadlab:

```powershell
docker compose up -d --build --wait
```

Dashboard: **http://localhost:8505**. OpenAPI: `/docs`. Porta su loopback,
massimo 2 GiB e una CPU, progetto Compose autonomo, nessuna modifica degli
altri servizi. Il volume esterno predefinito `aheadlab-hf` contiene i pesi
già disponibili nel workspace; configurabile con `CARBON_MODEL_VOLUME`.
La dashboard non scarica pesi e non comanda infrastrutture reali.

In questa sessione è stata verificata anche una scorciatoia offline che
riusa l'immagine di ricerca esistente. Dalla radice del monorepo:

```powershell
python carbonshift/scripts/dev_tools.py web
python carbonshift/scripts/dev_tools.py build
python carbonshift/scripts/dev_tools.py up
# Al termine:
python carbonshift/scripts/dev_tools.py stop
```

Per una macchina autonoma, dalla cartella `carbonshift`:

```powershell
$env:CARBON_MODEL_VOLUME = 'carbonshift-model-cache'
docker volume create carbonshift-model-cache
docker compose build
docker run --rm -v carbonshift-model-cache:/home/app/.cache/huggingface aheadlab-carbonshift python scripts/download_model.py
docker compose up -d --wait
```

Il download del modello è un passaggio esplicito con rete. I replay funzionano
senza caricare il modello: l'inferenza parte solo quando si carica un CSV
e si preme «Calcola in locale». Per un build senza libreria Timestral usare
`docker compose build --build-arg INSTALL_MODEL=false`; l'inferenza restituisce
un errore esplicito, mentre i replay restano disponibili.

## Cosa contiene

- Pianificazione: 54 replay con selezione di zona, data, energia e metodo.
- Finestre: durata 2/4/8 ore e scadenza 24/48/96, confronto grafico ed export CSV.
- Ricerca: tutti i metodi e distinzione fra test 2025 e controllo 2026.
- Dati propri: CSV `time,ci_g_per_kwh`, da 168 a 8.192 ore consecutive;
  timestamp ISO con fuso, dati finiti non negativi, massimo 2 MB nella UI.
  Quattro ore entro 96, consumo impostabile. Nessun invio a un servizio AI.
- Tema chiaro/scuro, interfaccia responsive, errori che conservano il replay
  precedente. I cambi ai parametri diventano effettivi premendo Confronta.

Il benchmark riguarda 4 ore entro 96 e confronto GBM; gli altri parametri
sono scenari esplorativi e non riscrivono il risultato pubblicato. L'energia
scala i kg, non modifica la percentuale del confronto. L'inferenza su un
CSV nuovo produce stime, non un beneficio già verificato.

## Riprodurre la ricerca

Fonte e attribuzione: [Khepri-TSFM v1.0.1](https://doi.org/10.5281/zenodo.23912503),
Eirik Botten Nicolaysen / EcoDeco AS. Dati derivati e previsioni CC BY 4.0,
commit fissato in [data/source.json](data/source.json). Sono scaricati circa
110 MiB, senza dati grezzi ENTSO-E né chiavi API. La directory raw è ignorata
da Git. I nostri risultati derivati conservano la medesima attribuzione.

Dalla radice Aheadlab, con l'immagine `aheadlab-capacity-validation` disponibile:

```powershell
python carbonshift/scripts/fetch_data.py
python carbonshift/scripts/run_isolated.py benchmark reproduce test report
```

Per preparare quella immagine nel workspace: seguire le istruzioni del
runner di Capacity Planner; non serve avviarne la dashboard. Il codice
scientifico CarbonShift non importa i moduli degli altri progetti.

In un ambiente Python autonomo, dalla cartella CarbonShift:

```bash
pip install -e '.[test,research,model]'
python scripts/fetch_data.py
python scripts/benchmark.py
pytest -q
python scripts/report.py
```

`reproduce.py` e il runner isolato assumono la cache Docker montata in
`/home/app/.cache/huggingface`; il runner è specifico Windows. La riproduzione
ricalcola 24 previsioni 5M sistematiche, non tutte le previsioni della fonte.
Le versioni dei pesi e della libreria sono fissate. Gli hash dei sorgenti
del benchmark e del protocollo sono salvati prima del confronto finale.

## Verifiche

23 test Python, tre test browser desktop/mobile e una inferenza reale 5M
attraverso l'API. Campione di 24 previsioni locali: tutte le finestre
coincidono con quelle ottenute dalle previsioni pubblicate dagli autori.
Circa 87 ms per previsione sul campione; picco RSS circa 497 MiB.

```powershell
python carbonshift/scripts/run_isolated.py test
python carbonshift/scripts/dev_tools.py browser
python carbonshift/scripts/check_live.py
```

Gli ultimi due comandi richiedono la sola dashboard CarbonShift avviata.
Per il frontend fuori dal workspace: `cd web`, `npm ci`, `npm run build` e
`BASE_URL=http://127.0.0.1:8505 npx playwright test`.

## API e limiti

`GET /api/meta`, `GET /api/research`, `POST /api/plan`, `POST /api/export`,
`POST /api/forecast`, `GET /api/doc/{research|protocol|math|decisions}`.
Contratti completi in `/docs`. Una sola inferenza concorrente per processo;
usare un unico worker. Il servizio è locale e privo di autenticazione.

La metrica è basata sul mix di produzione e non sui costi dell'elettricità.
Non simula ritardi di pubblicazione, fatturazione, costo dell'attesa,
concorrenza tra lavori o emissioni marginali. I dati 2025 potrebbero essere
presenti nel pretraining. Il controllo dopo il rilascio non basta a confermare
il beneficio. Non è una raccomandazione automatica a sostituire un sistema.

Codice originale Aheadlab MIT. Libreria Timestral Apache 2.0; pesi sotto
[licenza Mistral Modified MIT](https://huggingface.co/mistralai/Timestral-5M/blob/bdd20cfc15a3fea0e4cb5ccef37f8d3ca7aa335f/LICENSE).
I pesi non sono redistribuiti. Dati e risultati derivati:
[licenza CC BY 4.0](data/LICENSE-DATA) e [attribuzione](data/ATTRIBUTION.md).
