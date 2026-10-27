# aheadlab — Piano completo dei progetti

> Tre progetti portfolio di previsione su serie temporali con **Timestral** (Mistral AI).
> Obiettivo: dimostrare che so costruire pipeline dati + modelli di previsione + prodotto utilizzabile, misurando i risultati in modo onesto.
>
> Legenda: **[VERIFICATO]** = controllato su documentazione ufficiale · **[DA VERIFICARE]** = da controllare prima di scrivere codice · **[DECISIONE]** = scelta mia, modificabile

---

## Indice

0. [Panoramica e ordine di lavoro](#0-panoramica-e-ordine-di-lavoro)
1. [Struttura GitHub dell'organization](#1-struttura-github-dellorganization)
2. [Timestral: cosa so e cosa no](#2-timestral-cosa-so-e-cosa-no)
3. [Setup ambiente comune](#3-setup-ambiente-comune)
4. [Convenzioni comuni a tutti i repo](#4-convenzioni-comuni-a-tutti-i-repo)
5. [Progetto 1 — CloudGuard (costi cloud)](#5-progetto-1--cloudguard)
6. [Progetto 2 — StockSense (riordino magazzino)](#6-progetto-2--stocksense)
7. [Progetto 3 — SolarCast (fotovoltaico)](#7-progetto-3--solarcast)
8. [Sito GitHub Pages](#8-sito-github-pages)
9. [Licenze](#9-licenze)
10. [Checklist finale](#10-checklist-finale)
11. [Diario di lavoro](#11-diario-di-lavoro)

---

## 0. Panoramica e ordine di lavoro

| # | Progetto | Repo | Cosa fa | Difficoltà | Tempo stimato |
|---|----------|------|---------|------------|---------------|
| 1 | CloudGuard | `aheadlab/cloudguard` | Prevede i costi AWS e manda un allarme se un giorno esce dalla norma | Bassa | 2–3 giorni |
| 2 | StockSense | `aheadlab/stocksense` | Prevede vendite per prodotto e dice cosa riordinare | Media | 4–6 giorni |
| 3 | SolarCast | `aheadlab/solarcast` | Prevede la produzione fotovoltaica delle prossime 48 ore usando il meteo | Media-alta | 4–6 giorni |

**Ordine consigliato [DECISIONE]:** CloudGuard → StockSense → SolarCast.
- CloudGuard per primo perché è il più corto: serve a verificare che Timestral si installi e funzioni davvero. Se lì va tutto bene, gli altri due poggiano su basi solide.
- StockSense per secondo perché è il caso con il business più chiaro.
- SolarCast per ultimo perché usa le covariate (meteo futuro), la parte dell'API Timestral meno documentata.

**Regola d'oro per tutti e tre:** ogni progetto deve avere un **backtest** che confronta Timestral con almeno un metodo semplice. Un progetto che dice "uso l'AI" senza numeri non convince nessuno; uno che dice "migliora del X% rispetto al metodo classico, ecco come l'ho misurato" sì. Anche se Timestral perde in qualche caso, scriverlo è un punto a favore.

---

## 1. Struttura GitHub dell'organization

```
github.com/aheadlab
├── aheadlab              ← questo repo: piano, note, diario (privato o pubblico, a scelta)
├── .github               ← README pubblico dell'organization (pagina profilo)
│   └── profile/README.md
├── aheadlab.github.io    ← sito GitHub Pages → https://aheadlab.github.io
├── cloudguard
├── stocksense
└── solarcast
```

- **`.github`** (repo pubblico): il file `profile/README.md` appare nella pagina principale dell'organization. Ci metti 5 righe: cosa fa aheadlab, i tre progetti, link al sito.
- **`aheadlab.github.io`**: deve chiamarsi esattamente così, altrimenti il sito non va su `https://aheadlab.github.io`.
- **Topics da mettere su ogni repo** (Settings → About): `time-series`, `forecasting`, `timestral`, `python`, `machine-learning`, più uno specifico (`aws`, `ecommerce`, `solar-energy`).

---

## 2. Timestral: cosa so e cosa no

### 2.1 Fatti [VERIFICATO] (pagina ufficiale Hugging Face e blog Mistral)

- Famiglia di 4 modelli: **5M, 28M, 123M, 209M** parametri. Pesi: ~21 MB, ~111 MB, ~490 MB, ~837 MB.
- Gira su **CPU**, non serve GPU.
- Requisiti: **Python ≥ 3.10, torch ≥ 2.4**.
- Storico in input: fino a **32.768 passi temporali**.
- Orizzonte: fino a **1.024 passi** in un'unica chiamata. Oltre, il modello va avanti a blocchi usando le proprie previsioni.
- Output: **21 quantili**: 0.01, 0.05, 0.10, 0.15, … 0.85, 0.90, 0.95, 0.99.
- Input supportati: serie singola o multipla, covariate solo-passate e a futuro noto, numeriche o categoriche. Valori mancanti = `NaN`.
- Licenza pesi: **MIT modificata**. Nessun diritto per aziende con fatturato consolidato sopra 20 milioni $ (le fonti non concordano se mensile o annuo: leggere il file LICENSE su Hugging Face). Per me non è un problema.
- Codice della libreria: Apache 2.0.

Installazione:
```bash
pip install git+https://github.com/mistralai/timestral.git
```

Uso base (codice ufficiale):
```python
import numpy as np
import torch
from timestral import TimestralForecaster

model = TimestralForecaster.from_pretrained(
    "mistralai/Timestral-209M",
    device="cuda" if torch.cuda.is_available() else "cpu",
)

context = np.random.default_rng(42).standard_normal(1000).cumsum()
forecast = model.forecast(context, prediction_length=96)

median = forecast.median
lower, upper = forecast.quantile(0.1), forecast.quantile(0.9)
```

### 2.2 Cose [DA VERIFICARE] prima di scrivere codice serio

Leggere il README e i file in `src/` del repo `github.com/mistralai/timestral`:

1. **Forma degli array restituiti**: `forecast.median` è `(prediction_length,)`, oppure `(1, prediction_length)`, oppure un tensore torch? → Nel wrapper converto sempre con `np.asarray(...).squeeze()` e testo la forma.
2. **Più serie in una chiamata (batch)**: si può passare una lista o un array 2D? Cambia molto la velocità per StockSense (50 prodotti).
3. **Serie multivariate**: qual è il formato? (array `[variabili, tempo]`? `[tempo, variabili]`?)
4. **Covariate**: nomi dei parametri per covariate passate e future. Serve per SolarCast versione B.
5. **`quantile(q)` con q non tra i 21**: dà errore o interpola? Usare solo i 21 valori ufficiali per sicurezza.
6. **Cache del modello**: dove salva i pesi scaricati (dovrebbe essere la cache standard di Hugging Face, `~/.cache/huggingface`).

### 2.3 Regola architetturale [DECISIONE]

In ogni repo **Timestral si usa solo dentro un file**: `forecaster.py`. Il resto del codice chiama le mie funzioni, non la libreria. Se l'API è diversa da come penso, correggo un solo file.

```python
# forecaster.py — stesso file in tutti e tre i repo
from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
import numpy as np

QUANTILI_UFFICIALI = [0.01, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45,
                      0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.99]

@dataclass
class Previsione:
    mediana: np.ndarray
    p10: np.ndarray
    p90: np.ndarray
    p01: np.ndarray
    p99: np.ndarray

@lru_cache(maxsize=4)
def carica_modello(taglia: str = "28M"):
    import torch
    from timestral import TimestralForecaster
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return TimestralForecaster.from_pretrained(f"mistralai/Timestral-{taglia}", device=device)

def _np(x) -> np.ndarray:
    # gestisce sia numpy sia tensori torch
    if hasattr(x, "detach"):
        x = x.detach().cpu().numpy()
    return np.asarray(x, dtype=float).squeeze()

def prevedi(storico: np.ndarray, orizzonte: int, taglia: str = "28M") -> Previsione:
    storico = np.asarray(storico, dtype=float)
    if len(storico) > 32768:
        storico = storico[-32768:]          # limite di contesto ufficiale
    model = carica_modello(taglia)
    f = model.forecast(storico, prediction_length=orizzonte)
    return Previsione(
        mediana=_np(f.median),
        p10=_np(f.quantile(0.1)),
        p90=_np(f.quantile(0.9)),
        p01=_np(f.quantile(0.01)),
        p99=_np(f.quantile(0.99)),
    )
```

Primo test da fare (in tutti i repo, `tests/test_forecaster.py`):
```python
import numpy as np
from forecaster import prevedi

def test_forma_output():
    serie = np.sin(np.arange(500) * 2 * np.pi / 7) + 10
    p = prevedi(serie, orizzonte=14, taglia="5M")
    assert p.mediana.shape == (14,)
    assert np.all(p.p10 <= p.mediana + 1e-6)
    assert np.all(p.mediana <= p.p90 + 1e-6)
```
Se questo test passa, la base è solida.

---

## 3. Setup ambiente comune

### 3.1 Locale

```bash
# Python 3.11 consigliato [DECISIONE]
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# PyTorch solo CPU (molto più leggero della versione con CUDA)
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Timestral
pip install git+https://github.com/mistralai/timestral.git

# Comuni
pip install pandas numpy pyarrow duckdb statsforecast matplotlib plotly streamlit requests python-dotenv pytest
```

Nota: l'installazione di PyTorch è pesante (centinaia di MB). Normale che ci metta qualche minuto.

### 3.2 `requirements.txt` base (adattare per repo)

```
--extra-index-url https://download.pytorch.org/whl/cpu
torch>=2.4
timestral @ git+https://github.com/mistralai/timestral.git
pandas>=2.1
numpy>=1.26
pyarrow
duckdb
statsforecast
plotly
streamlit
requests
python-dotenv
pytest
```

[DA VERIFICARE] Se `timestral` viene pubblicato su PyPI ufficialmente, sostituire la riga git con `timestral==<versione>`. Esiste un fork su PyPI (`timecopilot-timestral`), ma **non** è il pacchetto ufficiale Mistral: non usarlo.

### 3.3 Segreti

- File `.env` locale (mai su git) + `.env.example` committato con le chiavi vuote.
- Su GitHub: Settings → Secrets and variables → Actions.

---

## 4. Convenzioni comuni a tutti i repo

### 4.1 Struttura cartelle

```
<progetto>/
├── README.md
├── LICENSE                  ← MIT [DECISIONE]
├── requirements.txt
├── .env.example
├── .gitignore               ← .venv, .env, data/raw, data/processed, __pycache__, *.parquet
├── data/
│   ├── raw/                 ← dati scaricati (NON su git)
│   └── processed/           ← dati puliti (NON su git)
├── src/<progetto>/
│   ├── __init__.py
│   ├── forecaster.py        ← unico punto di contatto con Timestral
│   ├── ingest.py            ← scarica/legge i dati
│   ├── prepare.py           ← pulizia e aggregazione
│   ├── baselines.py         ← metodi classici per il confronto
│   ├── backtest.py          ← misura degli errori
│   └── logic.py             ← logica di business (riordino / allarmi / fasce orarie)
├── app/
│   └── streamlit_app.py     ← dashboard demo
├── scripts/
│   └── run_backtest.py      ← genera la tabella risultati per il README
├── results/
│   ├── backtest.csv         ← SU git: sono i numeri da mostrare
│   └── *.png                ← grafici per il README
└── tests/
```

### 4.2 Metriche (stesse per tutti, così i README sono coerenti)

```python
# backtest.py — funzioni metriche
import numpy as np

def mae(reale, previsto):
    return float(np.mean(np.abs(np.asarray(reale) - np.asarray(previsto))))

def mase(reale, previsto, storico, m: int = 1):
    """Errore diviso per l'errore del metodo 'copia il valore di m passi fa' sullo storico.
    < 1 = meglio del metodo banale. m=7 per dati giornalieri con settimana, m=24 per orari."""
    storico = np.asarray(storico, dtype=float)
    scala = np.mean(np.abs(storico[m:] - storico[:-m]))
    if scala == 0:
        return float("nan")
    return mae(reale, previsto) / scala

def copertura(reale, basso, alto):
    """% di valori reali dentro la forchetta. Per la forchetta 10–90% deve stare vicino all'80%."""
    reale = np.asarray(reale)
    return float(np.mean((reale >= basso) & (reale <= alto)))
```

- **MASE**: dice se batte il metodo banale.
- **Copertura 10–90%**: dice se la forchetta è onesta. Se viene 50% la forchetta è troppo stretta; se viene 99% è troppo larga.

### 4.3 Backtest "a origine mobile" [DECISIONE]

Non un solo test sugli ultimi giorni, ma tanti tagli consecutivi: più robusto e più credibile.

```python
def backtest_mobile(serie, orizzonte, n_tagli, passo, funzioni: dict, m=7):
    """funzioni = {"timestral": f, "seasonal_naive": g, ...}, ognuna (storico, orizzonte) -> array mediana"""
    import pandas as pd
    righe = []
    for i in range(n_tagli):
        fine = len(serie) - orizzonte - i * passo
        storico, reale = serie[:fine], serie[fine:fine + orizzonte]
        for nome, f in funzioni.items():
            prev = f(storico, orizzonte)
            righe.append({"taglio": i, "modello": nome,
                          "mae": mae(reale, prev),
                          "mase": mase(reale, prev, storico, m)})
    return pd.DataFrame(righe)
```

### 4.4 README di ogni progetto — scaletta fissa

1. Titolo + una frase che dice cosa fa
2. GIF o screenshot della demo
3. Link alla demo online
4. "Il problema" (3 righe, linguaggio da cliente)
5. "Come funziona" (schema a blocchi)
6. **"Risultati"**: tabella backtest + grafico
7. "Limiti" (onestà)
8. "Eseguirlo in locale" (comandi copia-incolla)
9. Stack
10. Licenza + nota sulla licenza dei pesi Timestral

---

## 5. Progetto 1 — CloudGuard

### 5.1 In una frase
Prevede i costi AWS giornalieri per servizio, stima la spesa di fine mese con una forchetta e manda un allarme Telegram quando un giorno costa molto più del previsto.

### 5.2 Perché interessa a un cliente
- Le bollette cloud esplodono spesso per errore (istanza dimenticata accesa, log che crescono, loop di chiamate).
- AWS ha già strumenti nativi (Budgets, Cost Anomaly Detection), ma sono generici. Qui il valore è: semplicità, messaggio chiaro, multi-account, e lo stesso sistema riutilizzabile su Azure/GCP.

### 5.3 Dati

**Opzione A — AWS reale**
- API: AWS Cost Explorer, metodo `get_cost_and_usage`.
- Costo: circa 0,01 $ per chiamata [DA VERIFICARE sul listino AWS attuale]. Con 1–2 chiamate al giorno è trascurabile.
- Storico disponibile: circa gli ultimi 13–14 mesi [DA VERIFICARE].
- Cost Explorer va attivato nella console Billing (se mai attivato, i dati possono comparire dopo fino a 24 ore).
- Permesso IAM minimo: `ce:GetCostAndUsage`.
- Endpoint: regione `us-east-1` (Cost Explorer è globale ma il client si crea lì).

**Opzione B — dati sintetici (per la demo pubblica) [DECISIONE: farla comunque]**
La demo online non deve mostrare i miei costi reali. Generatore realistico:

```python
# src/cloudguard/synthetic.py
import numpy as np
import pandas as pd

def genera_costi(giorni=400, seed=7):
    rng = np.random.default_rng(seed)
    date = pd.date_range(end=pd.Timestamp.today().normalize(), periods=giorni, freq="D")
    t = np.arange(giorni)
    weekend = (date.dayofweek >= 5).astype(float)

    servizi = {
        # base, trend al giorno, effetto weekend, rumore
        "Amazon EC2":  (40, 0.03, -0.25, 0.06),
        "Amazon RDS":  (18, 0.01, -0.05, 0.03),
        "Amazon S3":   (6,  0.01,  0.00, 0.04),
        "AWS Lambda":  (3,  0.005,-0.40, 0.15),
        "CloudWatch":  (2,  0.002, 0.00, 0.10),
    }
    righe = []
    picchi = []
    for nome, (base, trend, wk, rumore) in servizi.items():
        y = (base + trend * t) * (1 + wk * weekend) * rng.lognormal(0, rumore, giorni)
        # 3 anomalie casuali per servizio (x3–x6 per 1–3 giorni)
        for _ in range(3):
            i = int(rng.integers(30, giorni - 5))
            durata = int(rng.integers(1, 4))
            fattore = rng.uniform(3, 6)
            y[i:i + durata] *= fattore
            picchi.append({"servizio": nome, "inizio": date[i], "giorni": durata})
        righe.append(pd.DataFrame({"data": date, "servizio": nome, "costo": y.round(2)}))
    return pd.concat(righe, ignore_index=True), pd.DataFrame(picchi)
```
Il secondo valore restituito (lista dei picchi inseriti) serve per misurare quanti allarmi sono giusti.

### 5.4 Ingest AWS reale

```python
# src/cloudguard/ingest.py
import boto3
import pandas as pd
from datetime import date, timedelta

def scarica_costi_aws(giorni=400) -> pd.DataFrame:
    ce = boto3.client("ce", region_name="us-east-1")
    fine = date.today()                       # escluso
    inizio = fine - timedelta(days=giorni)
    righe, token = [], None
    while True:
        kwargs = dict(
            TimePeriod={"Start": inizio.isoformat(), "End": fine.isoformat()},
            Granularity="DAILY",
            Metrics=["UnblendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        )
        if token:
            kwargs["NextPageToken"] = token
        r = ce.get_cost_and_usage(**kwargs)
        for giorno in r["ResultsByTime"]:
            d = giorno["TimePeriod"]["Start"]
            for g in giorno["Groups"]:
                righe.append({
                    "data": pd.Timestamp(d),
                    "servizio": g["Keys"][0],
                    "costo": float(g["Metrics"]["UnblendedCost"]["Amount"]),
                })
        token = r.get("NextPageToken")
        if not token:
            break
    return pd.DataFrame(righe)
```
[DA VERIFICARE] Se il periodo richiesto è più vecchio dello storico disponibile, AWS risponde con errore: in quel caso ridurre `giorni`.

### 5.5 Preparazione

```python
# src/cloudguard/prepare.py
import pandas as pd

def tabella_giornaliera(df: pd.DataFrame, min_giorni=60) -> pd.DataFrame:
    """Righe = date, colonne = servizi, giorni mancanti = 0."""
    piv = df.pivot_table(index="data", columns="servizio", values="costo", aggfunc="sum")
    piv = piv.asfreq("D").fillna(0.0)
    # tengo solo servizi con abbastanza storico e costo non trascurabile
    attivi = (piv > 0).sum() >= min_giorni
    rilevanti = piv.sum() >= 1.0
    return piv.loc[:, attivi & rilevanti]
```
- I costi di "ieri" su AWS possono non essere definitivi: [DECISIONE] l'allarme lavora sul giorno **prima di ieri**, oppure segnala "dato provvisorio".

### 5.6 Logica di business

**A) Stima fine mese**
```python
# src/cloudguard/logic.py
import numpy as np
import pandas as pd
from .forecaster import prevedi

def stima_fine_mese(serie: pd.Series, taglia="5M"):
    oggi = serie.index[-1]
    fine_mese = oggi + pd.offsets.MonthEnd(0)
    mancanti = (fine_mese - oggi).days
    speso = serie[serie.index.to_period("M") == oggi.to_period("M")].sum()
    if mancanti == 0:
        return {"speso": speso, "stima": speso, "basso": speso, "alto": speso}
    p = prevedi(serie.values, orizzonte=mancanti, taglia=taglia)
    return {
        "speso": float(speso),
        "stima": float(speso + p.mediana.sum()),
        "basso": float(speso + p.p10.sum()),
        "alto":  float(speso + p.p90.sum()),
    }
```
Nota da mettere nel README: sommare i quantili giornalieri non dà il quantile esatto del totale. È un'approssimazione **prudente** (la forchetta viene un po' più larga del vero).

**B) Allarme anomalia**
```python
def controlla_giorno(serie: pd.Series, taglia="5M", soglia_q="p99", minimo_euro=5.0):
    storico, reale = serie.values[:-1], float(serie.values[-1])
    p = prevedi(storico, orizzonte=1, taglia=taglia)
    alto = float(getattr(p, soglia_q)[0]) if np.ndim(getattr(p, soglia_q)) else float(getattr(p, soglia_q))
    atteso = float(np.atleast_1d(p.mediana)[0])
    anomalia = reale > alto and (reale - atteso) >= minimo_euro
    return {"reale": reale, "atteso": atteso, "soglia": alto, "anomalia": anomalia}
```
- `minimo_euro`: evita allarmi su servizi da pochi centesimi (da 0,02 $ a 0,10 $ è "x5" ma non interessa a nessuno).

### 5.7 Baseline per il confronto
1. **Seasonal naive settimanale**: domani = stesso giorno della settimana scorsa.
2. **Media mobile 28 giorni.**
3. Per le anomalie: **regola fissa** "allarme se costo > media 28 gg + 3 × deviazione standard".

### 5.8 Backtest

**Previsione:**
- Orizzonte 7 e 30 giorni, 20 tagli con passo 7 giorni, per ogni servizio.
- Metriche: MASE (m=7), copertura 10–90%.

**Anomalie (sui dati sintetici, dove so dove sono i picchi):**
- Per ogni giorno degli ultimi 300: esegui `controlla_giorno` con storico fino al giorno prima.
- Conta: picchi trovati / picchi totali (**recall**) e allarmi giusti / allarmi totali (**precisione**).
- Confronta con la regola fissa "media + 3 deviazioni".
- Tabella nel README:

| Metodo | Picchi trovati | Falsi allarmi | Precisione |
|---|---|---|---|
| Timestral (soglia p99) | ? / 15 | ? | ? |
| Media + 3σ | ? / 15 | ? | ? |

Attenzione: dopo un picco, lo storico contiene il picco stesso e il modello può "abituarsi". Va bene, è realistico: annotare il comportamento.

### 5.9 Alert Telegram
1. Su Telegram parla con **@BotFather** → `/newbot` → ottieni il token.
2. Scrivi un messaggio al tuo bot, poi apri `https://api.telegram.org/bot<TOKEN>/getUpdates` → trovi il tuo `chat_id`.
3. Codice:
```python
# src/cloudguard/notify.py
import os, requests

def invia_telegram(testo: str):
    token = os.environ["TELEGRAM_TOKEN"]
    chat = os.environ["TELEGRAM_CHAT_ID"]
    r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      json={"chat_id": chat, "text": testo}, timeout=15)
    r.raise_for_status()
```
Formato messaggio:
```
⚠️ CloudGuard — anomalia
Amazon EC2 il 25/10: 187,40 $ (atteso ~42 $, soglia 61 $)
Stima fine mese: 2.150 $ (forchetta 1.980 – 2.390 $)
```

### 5.10 Automazione giornaliera (GitHub Actions)

`.github/workflows/daily.yml`:
```yaml
name: daily-check
on:
  schedule:
    - cron: "17 6 * * *"     # 06:17 UTC ogni giorno
  workflow_dispatch: {}       # avvio manuale dal tab Actions
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      - run: pip install -r requirements.txt
      - run: python -m cloudguard.daily
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
          CLOUDGUARD_MODE: aws      # oppure "synthetic"
```
- Ogni esecuzione scarica di nuovo i dati (1 chiamata): non serve salvare uno stato.
- Il modello 5M pesa ~21 MB: il download a ogni esecuzione è ok. Per velocizzare: `actions/cache` sulla cartella `~/.cache/huggingface`.
- Le Actions schedulate sui repo pubblici si disattivano dopo un periodo senza commit [DA VERIFICARE la durata attuale, storicamente 60 giorni].
- Le chiavi AWS: usare un utente IAM dedicato con il solo permesso `ce:GetCostAndUsage`.

### 5.11 Dashboard Streamlit
- Selettore servizio.
- Grafico: storico ultimi 90 giorni + previsione 30 giorni con banda 10–90% (plotly, area semitrasparente).
- Riquadro: speso questo mese / stima fine mese / forchetta.
- Tabella: ultimi allarmi.
- In modalità demo usa sempre i dati sintetici.

### 5.12 Limiti da dichiarare nel README
- Servizi nuovi senza storico → niente previsione affidabile per qualche settimana.
- Il dato di ieri può essere provvisorio.
- Sconti, crediti, Savings Plans e rimborsi possono creare salti non "anomali" (valutare `NetUnblendedCost` o escludere i record di credito).
- Soglie da tarare per ogni cliente.

### 5.13 Checklist CloudGuard
- [ ] Test `forecaster` passa (forma output, ordine quantili)
- [ ] Generatore sintetico + grafico
- [ ] Backtest previsione → `results/backtest.csv`
- [ ] Backtest anomalie → tabella recall/precisione
- [ ] Bot Telegram funzionante
- [ ] GitHub Action giornaliera (prima in modalità sintetica)
- [ ] Prova con un account AWS reale (anche piccolo)
- [ ] Dashboard Streamlit online
- [ ] README completo con risultati

---

## 6. Progetto 2 — StockSense

### 6.1 In una frase
Prevede le vendite giornaliere di ogni prodotto di un e-commerce e produce la lista di cosa riordinare, quanto e entro quando.

### 6.2 Perché interessa a un cliente
- Troppa merce = soldi fermi in magazzino. Troppo poca = vendite perse.
- I piccoli negozi riordinano "a occhio". Esistono app a pagamento per Shopify che fanno questo (es. Prediko, Inventory Planner): il mercato paga [DA VERIFICARE prezzi e stato attuale delle app concorrenti].

### 6.3 Dati

**Dataset principale: Online Retail II (UCI Machine Learning Repository)**
- E-commerce UK reale, transazioni dal 01/12/2009 al 09/12/2011, circa 1 milione di righe.
- Download: cercare "Online Retail II" sul sito UCI ML Repository → file Excel.
- File Excel con **due fogli** (uno per anno) [DA VERIFICARE nomi esatti dei fogli].
- Colonne [DA VERIFICARE all'apertura]: `Invoice`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`, `Price`, `Customer ID`, `Country`.
- Fatture che iniziano con **"C"** = annullate.
- **Non contiene giacenze di magazzino** → le simulo (vedi 6.7) e lo dichiaro.

**Opzionale, per la versione "vera": Shopify**
- Account Shopify Partners gratuito → crea un development store.
- Crea una custom app → Admin API (GraphQL) con permessi lettura `orders`, `products`, `inventory`.
- Popola il negozio con prodotti e ordini di prova (script che crea ordini con lo stesso andamento del dataset UCI).
- [DA VERIFICARE] Le policy attuali di Shopify su custom app e app pubbliche: se si vuole vendere l'app sull'App Store serve la review di Shopify.

### 6.4 Ingest

```python
# src/stocksense/ingest.py
import pandas as pd
from pathlib import Path

RAW = Path("data/raw/online_retail_II.xlsx")
OUT = Path("data/processed/transazioni.parquet")

def converti_una_volta():
    """Leggere l'Excel è lento (minuti): lo converto in parquet una sola volta."""
    if OUT.exists():
        return pd.read_parquet(OUT)
    fogli = pd.read_excel(RAW, sheet_name=None)          # tutti i fogli; serve openpyxl
    df = pd.concat(fogli.values(), ignore_index=True)
    df.columns = [c.strip() for c in df.columns]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False)
    return df
```
Aggiungere `openpyxl` ai requirements.

### 6.5 Pulizia e aggregazione

```python
# src/stocksense/prepare.py
import pandas as pd

def pulisci(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Invoice"] = df["Invoice"].astype(str)
    df = df[~df["Invoice"].str.startswith("C")]          # annullate
    df = df[(df["Quantity"] > 0) & (df["Price"] > 0)]    # resi, omaggi, rettifiche
    df["StockCode"] = df["StockCode"].astype(str).str.strip().str.upper()
    # codici non-prodotto (spese spedizione, commissioni, rettifiche)
    non_prodotti = {"POST", "DOT", "M", "MANUAL", "BANK CHARGES", "AMAZONFEE", "C2", "ADJUST", "D", "S", "PADS", "CRUK", "TEST001", "TEST002"}
    df = df[~df["StockCode"].isin(non_prodotti)]
    df["giorno"] = pd.to_datetime(df["InvoiceDate"]).dt.normalize()
    return df

def vendite_giornaliere(df: pd.DataFrame, top_n=50) -> pd.DataFrame:
    """Righe = giorni (calendario completo), colonne = top N prodotti, giorni senza vendite = 0."""
    agg = df.groupby(["giorno", "StockCode"])["Quantity"].sum().unstack(fill_value=0)
    top = df.groupby("StockCode")["Quantity"].sum().nlargest(top_n).index
    agg = agg[top]
    calendario = pd.date_range(agg.index.min(), agg.index.max(), freq="D")
    return agg.reindex(calendario, fill_value=0)
```

Controlli da fare a mano (Jupyter) e annotare nel diario:
1. **Giorni sempre a zero**: probabilmente il negozio è chiuso (es. un giorno della settimana, Natale). [DA VERIFICARE] Se un giorno della settimana è sempre 0, decidere: toglierlo dalla serie oppure lasciarlo (il modello impara lo zero). [DECISIONE] Lasciarlo, è più realistico.
2. **Ordini enormi isolati**: ci sono ordini singoli con quantità enormi (anche decine di migliaia di pezzi), a volte poi annullati. Regola: tagliare i valori giornalieri sopra il 99,5° percentile della serie di quel prodotto, solo per il calcolo del modello (annotarlo).
3. **Prodotti a vendita sporadica**: anche nel top 50 alcuni possono avere molti zeri. Calcolare la % di giorni con vendite > 0 per prodotto e annotarla.
4. **Dicembre 2010**: picco natalizio. Ottimo test per vedere se il modello coglie la stagionalità annuale (con ~2 anni di storico può farlo solo in parte).

### 6.6 Previsione

- Granularità: **giornaliera**. Orizzonte: **30 giorni**. Modello: **28M** [DECISIONE: buon compromesso].
- Ciclo sui 50 prodotti (oppure batch se l'API lo permette, vedi 2.2).
- Tempo atteso su CPU: pochi secondi in totale (stime ufficiali di latenza: decine/centinaia di millisecondi per previsione).

```python
# src/stocksense/forecast_all.py
import pandas as pd
from .forecaster import prevedi

def prevedi_tutti(vendite: pd.DataFrame, orizzonte=30, taglia="28M") -> dict:
    risultati = {}
    for sku in vendite.columns:
        risultati[sku] = prevedi(vendite[sku].values, orizzonte, taglia)
    return risultati
```

### 6.7 Logica di riordino

**Giacenze simulate [DECISIONE]:** per ogni prodotto, giacenza attuale = vendite reali degli ultimi N giorni × fattore casuale tra 0,3 e 2 (alcuni prodotti in esaurimento, altri sovraccarichi). Seed fisso, dichiarato nel README.

**Parametri per prodotto (da file `config/prodotti.csv`, con valori di default):**
- `lead_time_giorni`: tempo di consegna del fornitore (default 14)
- `ciclo_riordino_giorni`: ogni quanto si fanno ordini (default 7)
- `lotto_minimo`: quantità minima ordinabile (default 1)
- `livello_servizio`: quantile per la scorta di sicurezza (default 0.9)

**Calcolo:**
```python
# src/stocksense/logic.py
import math

def calcola_riordino(prev, giacenza, in_arrivo=0, lead_time=14, ciclo=7, lotto_minimo=1, livello="p90"):
    finestra = lead_time + ciclo                      # devo coprire fino al prossimo riordino
    domanda_mediana = float(prev.mediana[:finestra].sum())
    domanda_alta = float(getattr(prev, livello)[:finestra].sum())
    scorta_sicurezza = max(domanda_alta - domanda_mediana, 0)
    fabbisogno = domanda_mediana + scorta_sicurezza
    disponibile = giacenza + in_arrivo
    da_ordinare = max(fabbisogno - disponibile, 0)
    if da_ordinare > 0:
        da_ordinare = max(math.ceil(da_ordinare), lotto_minimo)

    # giorni di copertura: quanti giorni dura la giacenza secondo la mediana
    cumulata, giorni_copertura = 0.0, len(prev.mediana)
    for i, v in enumerate(prev.mediana):
        cumulata += max(v, 0)
        if cumulata > giacenza:
            giorni_copertura = i
            break

    if giorni_copertura <= lead_time:
        urgenza = "URGENTE"        # finisce prima che arrivi un nuovo ordine
    elif da_ordinare > 0:
        urgenza = "DA ORDINARE"
    else:
        urgenza = "OK"
    return {
        "domanda_prevista": round(domanda_mediana, 1),
        "scorta_sicurezza": round(scorta_sicurezza, 1),
        "giacenza": giacenza,
        "giorni_copertura": giorni_copertura,
        "da_ordinare": da_ordinare,
        "urgenza": urgenza,
    }
```
- Nota onesta: la mediana può essere leggermente negativa o frazionaria → la tronco a 0 e arrotondo per eccesso le quantità da ordinare.
- Nota onesta: somma dei quantili = approssimazione prudente (vedi CloudGuard).
- **Effetto stockout:** se nello storico un prodotto era esaurito, le "0 vendite" non sono "0 domanda". Il dataset non lo dice. Dichiararlo.

### 6.8 Baseline per il confronto
1. **Seasonal naive (7 giorni)**
2. **Media mobile 28 giorni**
3. **AutoETS** (statsforecast)
4. Opzionale: **Croston/ADIDA** (statsforecast) per i prodotti a vendita sporadica: sono i metodi classici per quel caso.

```python
# src/stocksense/baselines.py
import pandas as pd
from statsforecast import StatsForecast
from statsforecast.models import SeasonalNaive, AutoETS, CrostonClassic

def prevedi_baseline(vendite: pd.DataFrame, orizzonte: int) -> pd.DataFrame:
    lungo = (vendite.reset_index(names="ds")
                    .melt(id_vars="ds", var_name="unique_id", value_name="y"))
    sf = StatsForecast(
        models=[SeasonalNaive(season_length=7), AutoETS(season_length=7), CrostonClassic()],
        freq="D",
        n_jobs=-1,
    )
    return sf.forecast(df=lungo, h=orizzonte)
```
[DA VERIFICARE] Nelle versioni recenti di statsforecast il formato del risultato (colonna `unique_id` come colonna o come indice) è cambiato nel tempo: controllare con la versione installata.

### 6.9 Backtest
- Orizzonte 30 giorni, 8 tagli con passo 30 giorni (copre circa gli ultimi 8 mesi del dataset, Natale 2011 incluso solo in parte).
- Per ogni prodotto e taglio: MASE (m=7) di Timestral 5M, 28M, 209M e delle baseline.
- Risultato aggregato: **media geometrica del MASE** (come fanno i benchmark ufficiali) + quante volte ogni modello vince.
- **Test di business (il più convincente):** simula 6 mesi di gestione magazzino con ogni metodo. Ogni settimana il sistema decide quanto ordinare, la merce arriva dopo il lead time, le vendite reali consumano la giacenza. Misura:
  - giorni di esaurimento (vendite perse)
  - giacenza media (soldi fermi)
  Tabella finale:

| Metodo | Giorni esaurito (tot) | Giacenza media (pezzi) | Vendite perse |
|---|---|---|---|
| Timestral 28M | ? | ? | ? |
| AutoETS | ? | ? | ? |
| Media mobile | ? | ? | ? |

Questa tabella è quella che un negoziante capisce. È la parte più importante del README.

### 6.10 Dashboard Streamlit
- **Pagina 1 "Da fare oggi"**: tabella prodotti ordinata per urgenza (rosso/giallo/verde), colonne della funzione `calcola_riordino`, bottone "Scarica CSV ordine".
- **Pagina 2 "Prodotto"**: selettore SKU + descrizione, grafico storico 120 giorni + previsione 30 con banda 10–90%, curva giacenza prevista che scende fino a zero.
- **Pagina 3 "Risultati"**: tabella backtest e simulazione.
- **Sidebar**: lead time, ciclo, livello servizio modificabili → ricalcolo istantaneo.

### 6.11 Versione Shopify (fase 2, opzionale)
1. Dev store + custom app.
2. Query GraphQL: ordini (righe con prodotto/variante, quantità, data) e livelli di inventario per location.
3. Stessa pipeline: ordini → vendite giornaliere per variante → previsione → riordino.
4. Output: CSV, email settimanale, oppure tag/metafield sul prodotto.
5. [DA VERIFICARE] limiti di rate dell'API GraphQL Shopify e paginazione (cursor).

### 6.12 Limiti da dichiarare
- Giacenze simulate (il dataset non le ha).
- Stockout passati non visibili.
- Promozioni non presenti nei dati.
- Prodotti nuovi senza storico: servono regole (es. usare la media di prodotti simili).
- Prodotti sporadici: errore alto per qualsiasi metodo.

### 6.13 Checklist StockSense
- [ ] Excel → parquet
- [ ] Pulizia + note su anomalie dei dati nel diario
- [ ] Vendite giornaliere top 50
- [ ] Previsioni Timestral (5M, 28M, 209M)
- [ ] Baseline statsforecast
- [ ] Backtest MASE → `results/backtest.csv`
- [ ] Simulazione magazzino → `results/simulazione.csv`
- [ ] Logica riordino + test
- [ ] Dashboard 3 pagine
- [ ] Demo online
- [ ] README con le due tabelle
- [ ] (Fase 2) Shopify dev store

---

## 7. Progetto 3 — SolarCast

### 7.1 In una frase
Prevede la produzione di un impianto fotovoltaico per le prossime 48 ore usando lo storico e la previsione meteo, e dice in quali fasce orarie conviene consumare.

### 7.2 Perché interessa a un cliente
- Con l'autoconsumo e le comunità energetiche (CER), sapere quando si produrrà permette di spostare i consumi (lavatrici, pompe di calore, ricarica auto) nelle ore di sole.
- Per le aziende: pianificare carichi e batterie.

### 7.3 Dati

**PVGIS (Commissione Europea, JRC) — storico produzione**
- API gratuita, senza chiave.
- Endpoint orario: `seriescalc` [DA VERIFICARE versione attuale nell'URL, es. `v5_2` o `v5_3`].
- Esempio [DA VERIFICARE parametri]:
```
https://re.jrc.ec.europa.eu/api/v5_3/seriescalc?lat=45.82&lon=8.83&peakpower=1&loss=14&pvcalculation=1&angle=30&aspect=0&startyear=2020&endyear=2023&outputformat=json
```
  - `peakpower=1` → 1 kWp (poi scalo per la potenza reale)
  - `loss=14` → perdite di sistema 14%
  - `angle` = inclinazione, `aspect` = orientamento (0 = sud)
- Output: produzione oraria `P` in **watt** per l'impianto indicato, tempo in formato tipo `20200101:0010` in **UTC** [DA VERIFICARE formato esatto].
- Anni disponibili: dipendono dal database radiazione scelto [DA VERIFICARE ultimo anno disponibile].
- È produzione **simulata** da dati satellitari, non misurata. Va dichiarato.

**Open-Meteo — meteo storico e previsto**
- Gratuita, senza chiave, **solo uso non commerciale** sul piano gratuito. Per un prodotto a pagamento serve il piano commerciale [DA VERIFICARE prezzi].
- Storico (archive):
```
https://archive-api.open-meteo.com/v1/archive?latitude=45.82&longitude=8.83&start_date=2020-01-01&end_date=2023-12-31&hourly=shortwave_radiation,direct_radiation,diffuse_radiation,cloud_cover,temperature_2m&timezone=UTC
```
- Previsione:
```
https://api.open-meteo.com/v1/forecast?latitude=45.82&longitude=8.83&hourly=shortwave_radiation,direct_radiation,diffuse_radiation,cloud_cover,temperature_2m&forecast_days=3&timezone=UTC
```
- Usare **sempre `timezone=UTC`**, converti in ora italiana solo per la visualizzazione.

**Problema da conoscere:** per il backtest serve la previsione meteo **com'era** in passato, non il meteo reale osservato. Se uso il meteo osservato come "previsione", il risultato è troppo ottimista.
- Open-Meteo ha un'API di previsioni storiche ("Historical Forecast API") [DA VERIFICARE disponibilità e anni coperti].
- [DECISIONE] Prima versione: backtest con meteo osservato, dichiarato come "limite superiore". Seconda versione: previsioni storiche reali.

**Dati reali (bonus):** se ho accesso a un impianto vero (inverter Huawei FusionSolar, SMA, Fronius, SolarEdge…), i dati misurati valgono molto più di PVGIS. [DA VERIFICARE] API dell'inverter specifico.

### 7.4 Ingest

```python
# src/solarcast/ingest.py
import pandas as pd
import requests

def scarica_pvgis(lat, lon, anno_inizio, anno_fine, kwp=1.0, angle=30, aspect=0, loss=14):
    url = "https://re.jrc.ec.europa.eu/api/v5_3/seriescalc"       # [DA VERIFICARE versione]
    params = dict(lat=lat, lon=lon, peakpower=kwp, loss=loss, pvcalculation=1,
                  angle=angle, aspect=aspect, startyear=anno_inizio, endyear=anno_fine,
                  outputformat="json")
    r = requests.get(url, params=params, timeout=120)
    r.raise_for_status()
    righe = r.json()["outputs"]["hourly"]                          # [DA VERIFICARE struttura]
    df = pd.DataFrame(righe)
    df["ora"] = pd.to_datetime(df["time"], format="%Y%m%d:%H%M", utc=True).dt.floor("h")
    df["kwh"] = df["P"] / 1000.0                                    # W medi in un'ora → kWh
    return df[["ora", "kwh"]].set_index("ora")

def scarica_meteo_storico(lat, lon, inizio, fine):
    url = "https://archive-api.open-meteo.com/v1/archive"
    variabili = "shortwave_radiation,direct_radiation,diffuse_radiation,cloud_cover,temperature_2m"
    r = requests.get(url, params=dict(latitude=lat, longitude=lon, start_date=inizio,
                                      end_date=fine, hourly=variabili, timezone="UTC"), timeout=120)
    r.raise_for_status()
    h = r.json()["hourly"]
    df = pd.DataFrame(h)
    df["ora"] = pd.to_datetime(df["time"], utc=True)
    return df.drop(columns="time").set_index("ora")

def scarica_meteo_previsto(lat, lon, giorni=3):
    url = "https://api.open-meteo.com/v1/forecast"
    variabili = "shortwave_radiation,direct_radiation,diffuse_radiation,cloud_cover,temperature_2m"
    r = requests.get(url, params=dict(latitude=lat, longitude=lon, hourly=variabili,
                                      forecast_days=giorni, timezone="UTC"), timeout=60)
    r.raise_for_status()
    df = pd.DataFrame(r.json()["hourly"])
    df["ora"] = pd.to_datetime(df["time"], utc=True)
    return df.drop(columns="time").set_index("ora")
```

### 7.5 Preparazione
```python
# src/solarcast/prepare.py
def unisci(produzione, meteo):
    df = produzione.join(meteo, how="inner").sort_index()
    df = df.asfreq("h")                     # ore mancanti → NaN (Timestral accetta NaN)
    return df
```
Controlli:
1. Correlazione `kwh` vs `shortwave_radiation`: deve essere alta (> 0,9). Se è bassa → errore di fuso orario (sfasamento di 1 ora). Provare a spostare di ±1 ora e vedere quale correlazione è migliore.
2. Notte: produzione = 0. Ok.
3. Ora legale: lavorando in UTC il problema non esiste. Solo nella dashboard converti in `Europe/Rome`.

### 7.6 Versioni del modello

**Versione A — solo storico produzione**
```python
p = prevedi(df["kwh"].values[-24*365:], orizzonte=48, taglia="28M")
```
- Ci si aspetta: buona forma giornaliera (alba, picco, tramonto), ma non sa se domani è nuvoloso.

**Versione B — storico + meteo previsto come covariata a futuro noto**
- È il punto forte di Timestral secondo Mistral.
- [DA VERIFICARE] Firma esatta. Pseudo-codice (NOMI DEI PARAMETRI INVENTATI, da sostituire con quelli veri del README):
```python
# PSEUDO-CODICE — NON FUNZIONA COSÌ COM'È
f = model.forecast(
    target=storico_kwh,                          # (T,)
    future_covariates=radiazione_storico_piu_futuro,   # (T + 48,) oppure (n_cov, T+48)
    prediction_length=48,
)
```
- Covariate da provare in ordine: `shortwave_radiation` → + `cloud_cover` → + `temperature_2m`.
- Aggiungere una funzione `prevedi_con_covariate(...)` in `forecaster.py`, sempre unico punto di contatto.

**Versione C — baseline fisica semplice**
- Regressione lineare: `kwh = a × shortwave_radiation + b`, stimata sull'ultimo mese. Con la radiazione prevista dà la produzione prevista.
- Opzionale avanzato: **pvlib** per un modello fisico vero (posizione sole, inclinazione, temperatura celle).
- Se la versione B non batte la C, va scritto. È un risultato interessante comunque.

**Baseline banale:** "domani = oggi" (seasonal naive 24 ore).

### 7.7 Backtest
- Periodo di test: un anno intero (tutte le stagioni).
- Ogni giorno a mezzanotte UTC: prevedi le 48 ore successive con ogni versione.
- Metriche:
  - **MAE giornaliero in kWh** (produzione totale del giorno prevista vs reale) — capibile dal cliente
  - **MAE orario** solo sulle ore di luce
  - **Copertura 10–90%**
- Divisione per stagione (inverno/estate) e per tipo di giorno (sereno/nuvoloso/variabile, in base a `cloud_cover` medio).
- Tabella:

| Metodo | MAE giorno (kWh/kWp) | MAE giorni nuvolosi | Copertura 10–90% |
|---|---|---|---|
| Domani = oggi | ? | ? | – |
| Regressione su radiazione (C) | ? | ? | – |
| Timestral solo storico (A) | ? | ? | ? |
| Timestral + meteo (B) | ? | ? | ? |

Ricordare nel README: se il meteo usato è quello osservato e non previsto, i risultati di B e C sono **ottimisti**.

### 7.8 Logica di business: fasce consigliate
```python
# src/solarcast/logic.py
import pandas as pd

def fasce_migliori(prev_mediana, prev_p10, ore_utc, kwp, soglia_kw=None, durata_min_ore=2):
    """Restituisce le fasce (ora inizio, ora fine, kWh previsti) dove anche lo scenario pessimista (p10)
    supera la soglia. Default soglia = 40% della potenza nominale."""
    soglia = soglia_kw if soglia_kw is not None else 0.4 * kwp
    s = pd.Series(prev_p10 * kwp, index=ore_utc.tz_convert("Europe/Rome"))
    sopra = s >= soglia
    fasce, inizio = [], None
    for ora, ok in sopra.items():
        if ok and inizio is None:
            inizio = ora
        if not ok and inizio is not None:
            if (ora - inizio).total_seconds() / 3600 >= durata_min_ore:
                fasce.append((inizio, ora))
            inizio = None
    if inizio is not None:
        fasce.append((inizio, s.index[-1]))
    return fasce
```
- Uso il **p10** (scenario pessimista), non la mediana: se consiglio di accendere la lavatrice alle 12, voglio essere abbastanza sicuro che ci sia sole.

### 7.9 Messaggio Telegram mattutino
```
☀️ SolarCast — impianto 6 kWp (Varese)
Oggi: 18–26 kWh previsti (probabile 23)
Fasce migliori: 10:30–14:30
Domani: nuvoloso, 6–14 kWh
```
Stessa infrastruttura di CloudGuard (bot Telegram + GitHub Actions alle 06:00).

### 7.10 Dashboard Streamlit
- Input: città (geocoding gratuito di Open-Meteo [DA VERIFICARE endpoint `geocoding-api.open-meteo.com`]) oppure lat/lon, kWp, inclinazione, orientamento.
- Grafico 48 ore: mediana + banda 10–90% + barre radiazione prevista.
- Fasce consigliate evidenziate.
- Pagina "Risultati" con la tabella backtest.
- Cache: dati PVGIS e meteo storico salvati per località (non riscaricarli ogni volta).

### 7.11 Limiti da dichiarare
- Produzione PVGIS simulata, non misurata.
- La qualità dipende dalla previsione meteo.
- Neve, ombre, sporcizia, guasti non considerati.
- Open-Meteo gratuito solo per uso non commerciale.
- Backtest con meteo osservato = ottimista.

### 7.12 Checklist SolarCast
- [ ] Download PVGIS + verifica formato
- [ ] Download meteo storico + allineamento orari (correlazione > 0,9)
- [ ] Versione A
- [ ] Baseline C (regressione) + banale
- [ ] Leggere API covariate di Timestral
- [ ] Versione B
- [ ] Backtest per stagione e tipo di giorno
- [ ] (Opzionale) previsioni meteo storiche reali
- [ ] Fasce consigliate + Telegram
- [ ] Dashboard
- [ ] README con tabella

---

## 8. Sito GitHub Pages

### 8.1 Repo `aheadlab.github.io`
- Sito statico semplice [DECISIONE]: un solo `index.html` + CSS, oppure Astro/Hugo se voglio un blog.
- Settings → Pages → Source: "Deploy from a branch" → `main` / root.

### 8.2 Contenuto
1. **Hero**: "aheadlab — previsioni affidabili su CPU per e-commerce, energia e cloud"
2. **Tre card progetto**: titolo, una frase, immagine/GIF, 2 numeri chiave dal backtest, link a demo, repo e articolo.
3. **Approccio**: "Ogni progetto è confrontato con metodi classici. Pubblico anche dove l'AI non vince."
4. **Articoli** (uno per progetto, anche in italiano e inglese):
   - "Timestral contro i metodi classici: test su dati e-commerce reali"
   - "Allarme costi AWS con previsioni probabilistiche"
   - "Prevedere il fotovoltaico con meteo e AI su CPU"
5. **Contatti**: link a antoniotrento.net, email, LinkedIn.
6. Link dal portfolio principale `antoniotrento.net` → aheadlab.

### 8.3 Demo online — opzioni
- **Hugging Face Spaces** (CPU gratuita): adatto. [DA VERIFICARE] se Streamlit è ancora tra gli SDK diretti o va usato il template Docker.
- **Streamlit Community Cloud**: gratuito, collegato al repo GitHub. [DA VERIFICARE limiti RAM: PyTorch + modello devono starci; usare 5M o 28M].
- **VPS** piccola (es. 5 €/mese) con Docker se le gratuite non bastano.
- I pesi del modello si scaricano da Hugging Face al primo avvio: **non** metterli nel repo (licenza + dimensione).

---

## 9. Licenze

- **Codice dei miei repo**: MIT [DECISIONE].
- **Timestral**:
  - libreria: Apache 2.0
  - pesi: MIT modificata → non ridistribuirli nei repo, farli scaricare da Hugging Face
  - nota fissa nel README:
    > Questo progetto usa i modelli Timestral di Mistral AI. I pesi sono distribuiti da Mistral su Hugging Face con licenza MIT modificata, che esclude le aziende sopra una certa soglia di fatturato. Leggere la licenza prima di un uso commerciale.
- **Dati**:
  - Online Retail II: licenza indicata sulla pagina UCI [DA VERIFICARE, di solito CC BY 4.0] → citare la fonte
  - PVGIS: citare "PVGIS © European Union"
  - Open-Meteo: attribuzione richiesta [DA VERIFICARE testo esatto] + uso non commerciale
  - AWS: solo dati miei o sintetici, mai di altri

---

## 10. Checklist finale

**Organization**
- [ ] Repo `.github` con `profile/README.md`
- [ ] Repo `aheadlab.github.io` online
- [ ] Avatar/logo dell'organization
- [ ] Topics su tutti i repo

**Per ogni progetto**
- [ ] Test forecaster verde
- [ ] Backtest con almeno 2 baseline
- [ ] `results/` con CSV e grafici su git
- [ ] Demo online funzionante
- [ ] README secondo la scaletta (sezione 4.4)
- [ ] Sezione "Limiti" scritta
- [ ] Articolo sul sito

**Verifiche tecniche da chiudere**
- [ ] Forma output `forecast` (2.2 punto 1)
- [ ] Batch di più serie (2.2 punto 2)
- [ ] Formato multivariato (2.2 punto 3)
- [ ] Parametri covariate (2.2 punto 4)
- [ ] URL e formato PVGIS
- [ ] Formato Excel Online Retail II
- [ ] Prezzo Cost Explorer API
- [ ] Hosting demo (limiti RAM)

---

## 11. Diario di lavoro

> Annotare qui: data, cosa ho fatto, cosa ho scoperto, cosa non funzionava, decisioni prese.
> Soprattutto le risposte ai punti [DA VERIFICARE].

| Data | Progetto | Cosa | Note / scoperte |
|------|----------|------|-----------------|
| 2026-10-27 | — | Creata org `aheadlab` e repo piano | |
| | | | |
