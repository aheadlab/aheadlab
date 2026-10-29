# CloudGuard — guida operativa

Questa guida accompagna il [README](../README.md) (risultati e limiti) e il [contratto del progetto](../SPEC.md). Tutti i comandi seguenti partono dalla cartella `cloudguard/`, anche dopo l'esportazione in un repository separato.

## 1. Primo avvio senza account

```bash
python -m venv .venv
# Bash: source .venv/bin/activate
# PowerShell: .venv\Scripts\Activate.ps1
pip install -e .
python -m cloudguard.daily
streamlit run app/streamlit_app.py
```

La CLI stampa JSON per i servizi sintetici; non contatta AWS né invia messaggi. La data della demo è fissa, non quella del computer. La dashboard parte in baseline: scegliere un servizio, osservare storico/previsione e modificare il cutoff per vedere un mese non ancora concluso. La pagina Risultati permette di scegliere baseline o `timestral-full`.

Per Timestral installare prima PyTorch CPU e `requirements-model.txt`, come nel README. Un errore di caricamento non causa un fallback nascosto.

## 2. Uso Python e schema dei dati

Input della preparazione: DataFrame con `data` (giorno senza timezone), `servizio`, `costo` numerico finito, `valuta` e `estimated` booleano. Una tabella non può mescolare valute. I crediti possono produrre costi negativi. L'ingest AWS conserva inoltre metadati giornalieri in `DataFrame.attrs`, importanti quando una risposta non contiene gruppi: non perderli convertendo il frame in CSV prima della valutazione.

Esempio offline completo:

```python
import pandas as pd
from cloudguard.synthetic import genera_costi
from cloudguard.prepare import tabella_giornaliera
from cloudguard.logic import stima_fine_mese, controlla_giorno

raw, eventi = genera_costi()
tabella = tabella_giornaliera(raw)
serie = tabella['Amazon EC2']
mese = stima_fine_mese(serie.iloc[:-7], taglia='baseline')
allarme = controlla_giorno(
    serie, taglia='baseline',
    as_of=serie.index[-1] + pd.Timedelta(days=2),
    provisional_dates=tabella.attrs['provisional_dates'],
)
assert 'stima' in mese and 'valutato' in allarme
print(mese, allarme)
```

`stima_fine_mese` restituisce speso, stima, estremi euristici e giorni mancanti. Una baseline non genera una banda probabilistica: gli estremi sono `None`, salvo il mese già concluso. `controlla_giorno` restituisce `valutato=False` e un motivo quando il dato non è utilizzabile: non va interpretato come assenza certa di anomalie.

## 3. AWS e Telegram: attivazione separata

1. Attivare Cost Explorer nell'account e verificare il costo delle chiamate API.
2. Configurare la credential chain boto3 con un'identità dedicata e permesso minimo `ce:GetCostAndUsage`; non salvare chiavi nel codice.
3. Eseguire prima `python -m cloudguard.daily --mode aws --model baseline`: **contatta AWS**, ma non invia Telegram.
4. Controllare valuta, completezza, stato provvisorio e periodo disponibile. L'ingest Python accetta `giorni` per ridurre la richiesta se lo storico richiesto non è disponibile.
5. Solo per abilitare l'invio, esportare `TELEGRAM_TOKEN` e `TELEGRAM_CHAT_ID`, poi aggiungere `--send`. `.env` non viene caricato automaticamente; in Docker usare esplicitamente `--env-file` solo con un file locale protetto.

Non eseguire prove reali senza autorizzazione dell'account. Non incollare token in ticket, screenshot o log. Daily non ha recupero persistente dei giorni provvisori né deduplicazione: ripetere un invio può duplicare un messaggio. Non affidargli monitoraggio di produzione senza affrontare questi limiti.

## 4. Riprodurre e interpretare i report

```bash
python scripts/run_backtest.py --quick --model baseline --output results/my-smoke
python scripts/run_backtest.py --model 5M --output results/my-full
```

Usare cartelle nuove: la CLI sovrascrive gli artefatti omonimi nella destinazione. Per un confronto valido leggere `metadata.json` prima dei CSV: fonte sintetica, seed, servizi, cutoff di selezione, numero di fold, orizzonti e finestra anomalie.

- `backtest.csv`: un servizio/origine/orizzonte/modello per riga; `coverage80` vuoto per baseline.
- `anomalies.csv`: precisione, recall giornaliero e recall eventi sono misure diverse.
- `anomaly_days.csv`: dettaglio giornaliero degli allarmi valutati.
- `events.csv`: eventi artificialmente inseriti, non anomalie AWS osservate.

I 10 eventi nel periodo valutato non sono tutti i 15 eventi generati. Non trasformare il recall eventi 100% in una dichiarazione di recall giornaliero 100%.

## 5. Test e diagnosi

```bash
pytest -q
# Bash: RUN_MODEL_TESTS=1 pytest -q
# PowerShell: $env:RUN_MODEL_TESTS='1'; pytest -q
```

- **Nessun servizio:** verificare soglia minima di 60 giorni positivi, importi e cutoff.
- **Dato recente/provvisorio:** attendere la finalizzazione; il controllo lavora al più fino a due giorni prima e sospende la valutazione se il prefisso contiene giorni Estimated.
- **Errore AWS di periodo:** ridurre `giorni` nell'ingest; non trasformare l'errore in una serie di zeri.
- **Pesi non disponibili:** verificare installazione opzionale, rete e permessi della cache Hugging Face.
- **Banda mensile ampia:** è una somma euristica di quantili marginali, non un intervallo calibrato del totale.

## 6. Docker e repository autonomo

```bash
docker build --build-arg INSTALL_MODEL=true -t cloudguard .
docker run --rm -p 127.0.0.1:8501:8501 cloudguard
docker run --rm cloudguard pytest -q
```

Il container parte come utente non-root. Per conservare i pesi tra avvii aggiungere un volume su `/home/app/.cache/huggingface`. Non copiare `.env`, dati privati, cache o pesi nel repository. I workflow annidati diventano attivi solo quando `cloudguard/` è la radice del repository GitHub; quello daily incluso resta una demo sintetica senza invio.
