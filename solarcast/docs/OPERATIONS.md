# SolarCast — guida operativa

Il [README](../README.md) presenta risultati e limitazioni; il [contratto](../SPEC.md) definisce le unità e i confini del prodotto. Tutti i comandi partono dalla cartella `solarcast/`.

## 1. Tre modalità da non confondere

- **Demo retrospettiva sintetica:** disponibile senza rete dopo l'installazione; coordinate e geometria non cambiano il generatore artificiale.
- **PVGIS storico:** scarica produzione simulata e meteo osservato, previa attivazione nella dashboard. È un confronto retrospettivo oracle per i metodi che usano meteo futuro.
- **API operativa:** richiede produzione misurata recente fornita dall'utilizzatore e meteo previsto immediatamente successivo. Non è un connettore inverter né una modalità live già configurata nella dashboard.

```bash
python -m venv .venv
# Bash: source .venv/bin/activate
# PowerShell: .venv\Scripts\Activate.ps1
pip install -e .
streamlit run app/streamlit_app.py
python scripts/daily.py
```

Daily è sempre una demo retrospettiva dry-run. Nella dashboard selezionare origine storica, potenza e metodo. Un report senza p10 mostra fasce indicative, non prudenti. La pagina Risultati espone CSV e metadati dei report presenti.

## 2. Schema, unità e esempio offline

Storico: DataFrame orario UTC, indice crescente e univoco, colonna `kwh` normalizzata per 1 kWp. Per regressione e B servono anche `shortwave_radiation` (W/m²), `cloud_cover` (%) e `temperature_2m` (°C). Il futuro ha lo stesso schema meteo e comincia un'ora dopo l'ultimo target. Le covariate future di B devono essere finite.

Esempio senza pesi né rete:

```python
from solarcast.demo import synthetic
from solarcast.forecast import forecast
from solarcast.logic import fasce_migliori

data = synthetic()
history = data.iloc[:-48]
future = data.iloc[-48:].drop(columns='kwh')
result = forecast(history, future, method='radiation_regression', max_context=720)
blocks = fasce_migliori(
    result.frame['median'], result.frame.get('p10'),
    result.frame.index, kwp=6, durata_min_ore=2,
)
assert len(result.frame) == 48
assert result.metadata['weather'] == 'observed_oracle'
print(result.metadata, blocks)
```

`Forecast.frame` contiene `median`; A/B aggiungono `p10` e `p90`. Tutti sono in kWh/kWp. Moltiplicare per la potenza una sola volta: `fasce_migliori` lo fa già internamente. Restituisce inizio/fine in Europe/Rome, durata fisica, energia attesa e base usata. La fine è esclusiva; una fascia che arriva all'ultimo campione comprende anche quell'ora.

## 3. Meteo reale e API operativa

`scarica_pvgis(lat, lon, anno_inizio, anno_fine, ...)` richiede sempre 1 kWp per normalizzare la produzione; `P/1000` approssima l'energia oraria. `scarica_meteo_storico` usa archive; `scarica_meteo_previsto` usa forecast con date UTC e cache giornaliera. La cache è in `data/raw/`, separata per parametri della richiesta. Per una nuova previsione all'interno dello stesso giorno la cache può essere ancora quella del primo download: per un refresh deliberato usare una nuova cartella cache o rimuovere solo la relativa risposta.

Per una previsione davvero attuale:

1. Importare e normalizzare misure recenti dell'impianto, non dati PVGIS vecchi di anni.
2. Allineare le covariate storiche sulle stesse ore UTC; non convertire i buchi in produzione zero.
3. Scaricare il meteo previsto e selezionare esattamente le successive 48 ore contigue allo storico.
4. Installare PyTorch CPU e `requirements-model.txt` se si usa A/B.
5. Chiamare `forecast(history, future_weather, method='B', model='5M', operational=True)`.

Il controllo operativo richiede ultimo timestamp dello storico entro due ore dall'orologio corrente, non futuro. Controllare comunque freschezza effettiva delle misure: un timestamp recente non certifica la qualità del sensore. Non modificare l'orologio `now` per far passare dati vecchi come attuali.

## 4. Riprodurre i benchmark

```bash
python scripts/run_backtest.py --quick --output results/my-smoke
python scripts/run_backtest.py --data pvgis --model 5M --year 2023 --lat 45.82 --lon 8.83 --output results/my-pvgis
```

Il secondo comando richiede modello installato e rete al primo download. Legge anno scelto e precedente; il protocollo completo considera le origini fino al 30 dicembre per avere 48 ore osservate. `--angle`, `--aspect`, `--loss` controllano geometria/perdite; `--max-context` il contesto. Quick limita il contesto a 720 ore e usa quattro origini stagionali.

Usare una cartella nuova: i report omonimi vengono sovrascritti. `metadata.json` registra protocollo, fonte e richiesta; `daily.csv` conserva ogni origine/giorno/metodo; `summary.csv` raggruppa per stagione e cielo. Le stesse date compaiono in più origini: non sono campioni indipendenti.

Per interpretare i risultati distinguere energia giornaliera e errore orario diurno. La copertura include anche la notte. B/C con meteo osservato hanno un vantaggio informativo non disponibile in esercizio: il benchmark non misura la qualità della previsione meteo né il risparmio in bolletta.

## 5. Telegram, sicurezza e automazione

`solarcast.notify.telegram(message, token=None, chat_id=None, dry_run=True)` non legge automaticamente variabili d'ambiente. Il dry-run non invia. Per un invio reale il chiamante deve passare esplicitamente token, chat ID e `dry_run=False`; può leggere i valori da variabili d'ambiente protette, ma questa lettura è a carico del chiamante.

Il workflow e `scripts/daily.py` inclusi restano demo senza invio. Non attivare una notifica mattutina reale con produzione storica spacciata per oggi. Non stampare token o URL autenticati: eventuali errori HTTP della funzione di invio non hanno una sanitizzazione dedicata, quindi proteggere i log dell'integrazione. Nessun invio reale è stato collaudato con un bot personale.

## 6. Test, Docker e diagnosi

```bash
pytest -q
docker build --build-arg INSTALL_MODEL=true -t solarcast .
docker run --rm -p 127.0.0.1:8503:8501 solarcast
docker run --rm solarcast pytest -q
```

Test con pesi reali: Bash `RUN_MODEL_TESTS=1 pytest -q`; PowerShell `$env:RUN_MODEL_TESTS='1'; pytest -q`. La cache modelli persistente va montata in `/home/app/.cache/huggingface`, scrivibile dall'utente non-root.

- **Future must immediately follow target history:** correggere allineamento e periodo, senza rietichettare arbitrariamente le date.
- **Expected timezone-aware UTC timestamps:** fornire indice UTC consapevole del fuso; Europe/Rome è solo visualizzazione.
- **Nessuna fascia:** soglia non superata per la durata richiesta; non è un errore da correggere allargando artificialmente p10.
- **PVGIS/meteo falliscono:** controllare disponibilità anno, coordinate, condizioni del servizio e risposta HTTP. Non esiste fallback nascosto alla demo.
- **Unità troppo grandi:** verificare se il target è già energia totale; dividerlo per la potenza nominale prima dell'API e non scalare due volte.

Per pubblicazione commerciale verificare separatamente licenze dei pesi, attribuzione PVGIS/Open-Meteo e condizioni dell'API gratuita. Il repository non distribuisce dati grezzi o pesi, e non configura un deployment pubblico.
