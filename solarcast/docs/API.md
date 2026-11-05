# SolarCast HTTP API

Workspace locale retrospettivo, senza autenticazione: esporre solo localhost. Nessun invio Telegram o falsa previsione attuale da PVGIS storico.

- `GET /api/health`: `{status,app}`.
- `GET /api/meta`: default, sorgenti, modelli e metodi.
- `POST /api/forecast`: source synthetic/pvgis; model baseline/5M/28M/209M; method seasonal_naive24/radiation_regression/A/B; lat, lon, kwp (>0), angle, aspect; year 2006–2023; origin data opzionale (default 15 giugno dell'anno); max_context 24–32768; threshold kW opzionale; min_hours 1–24. A/B richiedono una taglia Timestral.
- PVGIS effettua rete solo quando richiesto esplicitamente; cache separata per geometria/periodo/località. La UI richiede una conferma prima di selezionare la sorgente pubblica.
- Risposta: app, source, model, method, as_of, origin, kwp, metrics, history, forecast, windows, days, metadata.
- History `{time,value}` e forecast `{time,median,radiation,actual,lower?,upper?}` sono già scalati per capacità; non moltiplicarli di nuovo. Radiazione resta W/m². Timestamp UTC, visualizzazione Europe/Rome.
- Windows: start/end ISO con fuso, hours, expected_kwh, basis p10 oppure median_indicative. Fine esclusiva.
- Days: date UTC, energy, lower?/upper? (somme marginali, non intervalli calibrati).
- `GET /api/reports`: `{reports:[{id,label,metadata}]}`.
- `GET /api/reports/{id}`: `{id,metadata,tables}` (array di righe CSV); ID solo dalla whitelist dei report disponibili.

Errori JSON detail: 422 parametri o origine errati, 400 dati incompatibili, 409 calcolo concorrente, 503 rete/dati/modello non disponibili, 404 risorsa sconosciuta. Un calcolo per processo; abort browser non interrompe l'inferenza. Nessun fallback nascosto. JSON non finiti diventano null. OpenAPI `/docs` e `/openapi.json`. Asset web/dist serviti dalla stessa applicazione.
