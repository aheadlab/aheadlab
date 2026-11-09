# Ricerca di un caso utile, 9 novembre 2026

Richiesta: trovare e verificare un beneficio pratico di Timestral rispetto a
metodi classici, poi costruire un quinto progetto autonomo. Non basta un MAE
inferiore. I quattro progetti e i loro risultati rimangono invariati.

1. Verificare le fonti primarie: il benchmark Coralogix dimostra accuratezza
   su telemetria privata, non risparmi operativi. L'annuncio Mistral descrive
   capacità e scenari, non certifica la nostra applicazione.
2. Esplorare un problema diverso dal dimensionamento: scegliere in anticipo
   una finestra di manutenzione o lavoro differibile che coincida con poco
   traffico. Decisione concreta: un orario, mantenendo uguale la durata.
   Misura: traffico osservato nella finestra, non errore della previsione.
3. Usare i dati e le previsioni V2 già esaminati esclusivamente come sviluppo.
   Conservare tutti i risultati esplorativi, anche contrari all'AI. Non
   presentarli come conferma indipendente.
4. Solo con evidenza preliminare adeguata, fissare politica, confronti e
   criterio di successo prima di un periodo finale nuovo. Includere orario
   fisso, profilo storico, giorno/settimana precedente e modelli statistici.
5. Costruire una demo sul risultato verificato, senza chiamare volume esposto
   utenti danneggiati o euro risparmiati. Se il test non conferma il beneficio,
   riportarlo senza fabbricare un esito positivo.

Risorse iniziali: host 31,3 GiB, circa 9,64 GiB liberi; otto servizi attivi.
Usare solo container temporanei, massimo 2 GiB e una CPU, rete disabilitata
per il calcolo. Nessun nuovo modello scaricato; dashboard esistenti spente
o lasciate nel loro stato iniziale. Verificare memoria e servizi alla fine.

Fonti consultate:
- https://mistral.ai/news/timestral/
- https://github.com/mistralai/timestral
- https://benchmarks.coralogix.com/timestral-benchmarks
- https://cesnet.github.io/cesnet-tszoo/cesnet_timeseries26/

## Esito e completamento

Il primo candidato, finestre di manutenzione CESNET, è stato scartato:
la media storica batte l'AI nel confronto esplorativo. I risultati sono
conservati in [window_screening.csv](window_screening.csv).

La ricerca è proseguita con il dataset pubblico
[Khepri-TSFM v1.0.1](https://doi.org/10.5281/zenodo.23912503): scegliere
quando svolgere un lavoro elettrico differibile. L'esplorazione sul primo
semestre 2025 è conservata in [carbon_screening.csv](carbon_screening.csv),
con tutte le durate e gli orizzonti provati. Il caso selezionato è un lavoro
di quattro ore entro 96, valutato successivamente su un periodo separato.

È stato completato [CarbonShift](../../carbonshift/README.md), quinto progetto
autonomo. Il [protocollo fissato](../../carbonshift/docs/PROTOCOL.md) misura
le emissioni attribuite nella finestra scelta a parità di energia e lavoro.
Sul test storico Timestral 5M migliora lo 0,66% rispetto a GBM (circa 144 g/MWh),
intervallo [0,12%; 1,20%]. Il controllo successivo al rilascio, di 14 giorni,
rimane inconcludente. Questo risultato non dimostra ROI o emissioni marginali
evitate in produzione. [Ricerca e limiti](../../carbonshift/docs/RESEARCH.md).

Completati dashboard, API, riproduzione locale di 24 previsioni, 23 test
Python, tre test browser e inferenza reale via API. Nei job scientifici la
RAM disponibile minima campionata è 8,51 GiB, con otto servizi invariati.
La dashboard e il modello CarbonShift sono stati fermati al termine;
Capacity Planner resta spento. Testi del portfolio e registro aggiornati.
