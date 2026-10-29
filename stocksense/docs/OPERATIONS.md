# StockSense — guida operativa

Consultare il [README](../README.md) per i risultati e il [contratto](../SPEC.md) per le convenzioni. Eseguire i comandi dalla cartella `stocksense/`, anche quando diventa un repository separato.

## 1. Primo avvio offline

```bash
python -m venv .venv
# Bash: source .venv/bin/activate
# PowerShell: .venv\Scripts\Activate.ps1
pip install -e .
streamlit run app/streamlit_app.py
```

La demo usa transazioni artificiali e giacenze simulate. Nella pagina **Da fare oggi** scegliere il modello e controllare data della decisione, priorità e quantità. Il pulsante CSV esporta solo righe con quantità da ordinare positiva: non invia ordini. **Prodotto** mostra storico, previsione e giacenza senza nuovi arrivi. **Risultati** legge la cartella indicata: per esempio `results/uci-28M` per il confronto completo reale, anziché lo smoke sintetico predefinito.

La data decisionale segue la fine dello storico: non è necessariamente oggi. Per rendere effettivi i parametri globali della sidebar, selezionare la checkbox di modifica per tutti gli SKU.

## 2. Dati reali e aggiornamento della cache

```bash
python -c "from stocksense.ingest import download_uci; download_uci()"
python -c "from stocksense.ingest import converti_una_volta; print(converti_una_volta().shape)"
```

Il primo comando scarica l'archivio UCI ufficiale; il secondo legge tutti i fogli e crea il parquet. La prima conversione può essere lenta. Percorsi: `data/raw/online_retail_II.xlsx`, `data/processed/transazioni.parquet` e manifest della cache. Questi dati non sono versionati.

Colonne necessarie: `Invoice`, `StockCode`, `Quantity`, `Price`, `InvoiceDate`. Sono accettati gli alias `InvoiceNo` e `UnitPrice`; il dataset demo/UCI contiene anche `Description` per la dashboard. Quantità/prezzi non positivi, cancellazioni e codici non prodotto vengono esclusi.

Sostituendo l'Excel, il suo SHA256 cambia e invalida sia il parquet sia i dati della dashboard. Se il file manca, la modalità UCI fallisce esplicitamente, senza passare al sintetico. Per nuovi dati personalizzati usare le API Python e verificare schema, licenza e significato degli zeri: non è previsto un connettore Shopify già operativo.

## 3. Configurazione per prodotto

`config/prodotti.csv` contiene intestazione e riga default:

```csv
sku,lead_time_giorni,ciclo_riordino_giorni,lotto_minimo,livello_servizio
*,14,7,1,0.9
10000,10,7,6,0.5
```

La seconda riga di dati è un esempio di override, non un parametro validato per UCI. I livelli supportati sono 0,5, 0,9 e 0,99; tempi e lotto devono essere interi positivi. Il lotto è una quantità minima, **non un multiplo**. Duplicati SKU e valori non supportati causano errore.

Il livello 0,9 seleziona una somma di p90 marginali, non garantisce un servizio del 90%. Con baseline puntuali non esiste scorta quantile. La disponibilità include gli ordini già in arrivo; la previsione deve coprire almeno lead time + ciclo.

## 4. Uso Python con dati e inventario espliciti

```python
import pandas as pd
from stocksense.demo import synthetic_transactions
from stocksense.prepare import pulisci, vendite_giornaliere
from stocksense.forecast_all import forecast
from stocksense.logic import calcola_riordino

clean = pulisci(synthetic_transactions(days=400, products=2))
cutoff = clean.giorno.max() - pd.Timedelta(days=60)
daily = vendite_giornaliere(clean, top_n=2, cutoff=cutoff)
sku = daily.columns[0]
pred = forecast(daily[sku].to_numpy(), h=30, model='moving_average')
ordine = calcola_riordino(
    pred, giacenza=20, in_arrivo=5,
    lead_time=14, ciclo=7, lotto_minimo=6,
)
assert ordine['da_ordinare'] >= 0
print(sku, ordine)
```

`giacenza=20` e `in_arrivo=5` sono valori illustrativi, non dati UCI. Per valutare fuori campione, non includere nel training le vendite del periodo da prevedere. Le API di backtest e simulazione rifiutano date duplicate, invertite o con giorni mancanti; un RangeIndex a passo uno rappresenta giorni consecutivi senza data.

## 5. Benchmark, simulazione e lettura risultati

```bash
python scripts/run_backtest.py --quick --data synthetic --model baseline --output results/my-smoke
# Richiede file UCI locale e dipendenze/pesi Timestral installati:
python scripts/run_backtest.py --data uci --model 28M --output results/my-uci-28M
```

Per installare il modello: `pip install torch --index-url https://download.pytorch.org/whl/cpu`, poi `pip install -r requirements-model.txt`. Ogni taglia viene confrontata con seasonal naive, media mobile e AutoETS. Full: 50 SKU, 8 fold di 30 giorni, simulazione 180 giorni; quick: 2 SKU, 2 fold di 28 giorni, simulazione 28 giorni. Non confrontare le due modalità come se avessero lo stesso protocollo.

Scegliere cartelle nuove per non sovrascrivere i report precedenti. Leggere prima `metadata.json`, poi:

- `backtest.csv` e `riepilogo.csv`: errori per caso e aggregati; la media geometrica zero può derivare da un solo caso perfetto.
- `simulazione.csv`: stockout, vendite perse, giacenza media per SKU-giorno.
- `inventario_giornaliero.csv`: audit di ordini, arrivi, consumi e pendenti; vendite perse non riportate come arretrati.
- `ordini.csv`: proposte di tutti i metodi alla fine dello storico, non ordini trasmessi.
- `diagnostica.csv`: quota di giorni con vendita nel training.

Il confronto p90 contro baseline puntuali scambia meno stockout con più capitale immobilizzato. Prima di una decisione commerciale servono giacenze reali, costi e obiettivi di servizio, non solo il minor errore di previsione.

## 6. Test, problemi comuni e Docker

```bash
pytest -q
docker build --build-arg INSTALL_MODEL=true -t stocksense .
docker run --rm -p 127.0.0.1:8502:8501 stocksense
docker run --rm stocksense pytest -q
```

Per i test reali: Bash `RUN_MODEL_TESTS=1 pytest -q`; PowerShell `$env:RUN_MODEL_TESTS='1'; pytest -q`. Senza variabile sono saltate esplicitamente due integrazioni.

- **File UCI assente nel container:** i dataset sono esclusi dal build; montarli esplicitamente in `/app/data/raw` o usare la demo. Il processo non-root deve poter scrivere in `/app/data/processed`.
- **Storico insufficiente:** diminuire la dimensione del protocollo o fornire più storico; non usare il target per selezionare prodotti o stimare il clipping.
- **Ordine inatteso:** verificare configurazione effettiva, orizzonte, giacenza simulata, pending e checkbox degli override.
- **Zero MASE geometrico:** guardare MAE e righe per SKU, non dichiarare accuratezza perfetta.

Nel repository esportato i workflow inclusi testano package e smoke; non effettuano ordini, deployment o download di credenziali. Nessuna integrazione Shopify è già attivata.
