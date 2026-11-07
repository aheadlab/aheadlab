# API locale

- `GET /api/health`: stato del processo.
- `GET /api/meta`: modelli, configurazione iniziale e serie disponibili.
- `POST /api/forecast`: previsione demo o replay e simulazione di capacità.
- `GET /api/research`: risultati, protocollo e replay del benchmark eseguito.
- `GET /docs`: schema OpenAPI interattivo.

Il POST accetta `source` (`synthetic`/`cesnet`), `series`, `model`, `throughput`,
`margin_pct`, `startup_hours`, `unit_cost`. Campi sconosciuti o fuori intervallo
sono rifiutati. I dati CESNET pubblicati sono replay delle previsioni salvate;
le variazioni dei parametri cambiano la simulazione, non il benchmark storico.

Un solo calcolo per processo; richieste concorrenti ricevono 409. Pesi assenti
producono 503, nessun fallback nascosto. Nessuna operazione su servizi esterni.
