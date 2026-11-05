# CloudGuard HTTP API

API locale senza autenticazione; esporre solo su localhost. Nessuna rotta AWS o di invio Telegram. Endpoint sincroni di calcolo eseguiti in thread, massimo un calcolo concorrente per processo.

- `GET /api/health`: `{status, app}`.
- `GET /api/meta`: modelli, servizi e default.
- `POST /api/forecast`: `{service: "Amazon EC2", model: "baseline", horizon: 30, cutoff_days: 7}`. Modelli baseline/5M/28M/209M, orizzonte 1–90, cutoff 0–28.
- Risposta: `app`, `source`, `model`, `as_of`, `currency`, `service`, `metrics`, `month`, `services`, `history`, `forecast`, `alerts`, `metadata`.
- `history`: `{time,value}`; `forecast`: `{time,median,lower?,upper?}`. La baseline non ha lower/upper.
- `month`: campi dominio `speso`, `stima`, `basso`, `alto`, `giorni_mancanti`. Estremi null quando non disponibili.
- `services`: totali degli ultimi 30 giorni e ultimo costo. `alerts`: risultati retrospettivi per il servizio selezionato, con nome del metodo; non notifiche inviate.
- `GET /api/reports`: `{reports:[{id,label,metadata}]}`.
- `GET /api/reports/{id}`: `{id,metadata,tables}`; le tabelle sono array di righe dei CSV pubblicabili. Sono esclusi i registri giornalieri più grandi. ID consentiti solo dalla lista; non sono percorsi filesystem.

Errori JSON `detail`: 422 parametri non validi, 400 dati incompatibili, 409 calcolo già in corso, 503 dati/modello/servizio non disponibili, 404 risorsa inesistente. NaN/Infinity diventano null nel JSON; nessun fallback nascosto. Annullare una richiesta browser non interrompe un'inferenza già iniziata sul server. OpenAPI in `/docs` e `/openapi.json`.

Il frontend compilato in `web/dist` è servito dalla stessa applicazione; nessuna necessità di CORS in produzione. Il proxy Vite è destinato allo sviluppo locale.
