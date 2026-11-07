# Aheadlab — note e testo per la pagina portfolio

Ricerca aggiornata al 7 novembre 2026. Questo documento prepara i contenuti della
pagina portfolio. I tre frontend originali restano intatti; Capacity Planner
è il quarto progetto, con dashboard e benchmark propri.

## Titolo proposto

**Quando un modello AI migliora davvero una previsione?**

## Introduzione pronta per la pagina

Ho costruito quattro applicazioni dimostrative per mettere alla prova Timestral,
un modello preaddestrato per serie temporali, in quattro contesti: costi cloud,
riordino di magazzino, produzione fotovoltaica e pianificazione della capacità
di rete. Ogni applicazione collega
una pipeline dati e un backend Python a un frontend React/TypeScript.

L'obiettivo della ricerca è misurare quando il modello aggiunge valore rispetto
a metodi semplici. Ho confrontato le previsioni con baseline statistiche,
controllato la separazione temporale dei dati e verificato come cambiano i
risultati quando si passa dall'errore previsionale alla decisione operativa.

I test mostrano capacità utili: Timestral migliora l'errore giornaliero delle
vendite, il profilo orario della produzione solare e la previsione del traffico
di rete rispetto alle baseline esaminate. Timestral è un modello di Mistral
specializzato in serie temporali: qui elabora sequenze di misure numeriche.
La ricerca distingue questi vantaggi previsionali dal valore delle
decisioni costruite sopra il modello. Le applicazioni devono ancora dimostrare
che quelle capacità producano un risparmio economico in produzione.

## Come leggere il risultato: modello, applicazione e decisione

Un risultato operativo deludente non identifica automaticamente il limite del
modello. Occorre verificare anche quali informazioni gli abbiamo fornito, quale
uscita abbiamo utilizzato e come l'abbiamo trasformata in una decisione.

In StockSense abbiamo sommato mediane giornaliere per stimare il fabbisogno.
La somma delle mediane non coincide in generale con la media o la mediana della
domanda totale. Le vendite intermittenti rendono particolarmente importante
questa distinzione. La sottostima osservata riguarda anche questa scelta di
integrazione: non dimostra che tutte le possibili applicazioni di Timestral al
riordino falliscano. Correggerla non garantisce, però, un vantaggio: una diversa
politica va sottoposta a un nuovo confronto equo. Anche i quantili marginali
richiedono calibrazione e non descrivono da soli la dipendenza fra giorni.

In CloudGuard, una previsione accurata di una crescita non stabilisce se quella
crescita sia desiderata. Riconoscere un incidente richiede una definizione del
comportamento accettabile e, quando disponibili, informazioni sui cambi pianificati.

Il modello può inoltre ridurre la necessità di addestramenti specifici per ogni
serie. Il costo di configurazione e manutenzione è una dimensione utile da
misurare, ma non è stato quantificato nei nostri esperimenti. Il supporto alla
previsione zero-shot è descritto nel [repository ufficiale Timestral](https://github.com/mistralai/timestral/).

**Sintesi editoriale:** abbiamo verificato vantaggi previsionali specifici;
stiamo validando come trasformarli in decisioni migliori. Né «AI inutile» né
«AI sempre migliore» descrivono i risultati.

## Quattro schede di ricerca

### StockSense — vendite e riordino

**Domanda:** una previsione giornaliera più precisa produce ordini migliori?

Dati reali Online Retail II, un singolo rivenditore, 50 prodotti selezionati
sul periodo di training e otto finestre di test da 30 giorni.

- Timestral 5M: MAE giornaliero 41,318, contro 49,692 di AutoETS: **−16,9%**.
- Sul totale venduto nei 30 giorni l'errore assoluto medio è invece 789,933
  contro 560,826: **+40,8%**. Il modello tende a sottostimare i volumi.
- Applicando a tutti la stessa regola di scorta, al quantile empirico di
  calibrazione 0,9 l'AI tiene **4,3% di pezzi in meno**, ma perde **0,9% di unità
  di vendita in più** rispetto ad AutoETS. Non è un confronto a pari capitale.

**Conclusione pubblicabile:** il miglioramento dell'errore giornaliero non si
traduce automaticamente in una migliore decisione di riordino. Occorre misurare
domanda cumulata, scorte e costi con una politica comparabile.

**Limiti da mostrare insieme ai numeri:** inventario simulato, sei finestre
di calibrazione, domanda ricavata dalle vendite registrate, costi economici
assenti. Nessuna dimostrazione di riduzione dei costi o aumento del profitto.

Fonti: [accuratezza](validation/results/stock_new_accuracy.csv),
[inventario](validation/results/stock_equal_policy_summary.csv),
[incertezza del confronto](validation/results/stock_new_paired.csv).

### CloudGuard — previsione dei costi e allarmi

**Domanda:** una previsione migliore riconosce anche gli incidenti di spesa?

Stress test sintetico: tre seed, tre servizi per seed, picchi, derive graduali
e aumenti permanenti pianificati. Questi ultimi non sono comunicati ai rilevatori.

- Entrambi i metodi trovano **9 picchi su 9** al primo giorno.
- Sulle derive graduali Timestral trova **1 evento su 9**, la regola media
  più tre deviazioni standard **5 su 9**.
- MAE a 7 giorni: **2,936** per Timestral contro **3,767** per la copia della
  settimana precedente. A 30 giorni il risultato si inverte: **4,895** contro
  **4,165**.

**Conclusione pubblicabile:** prevedere il comportamento futuro e riconoscere
un comportamento indesiderato sono obiettivi diversi. In questi scenari il
rilevatore AI non giustifica la sostituzione della regola semplice.

**Limiti da mostrare insieme ai numeri:** dati sintetici, soglie non calibrate
a pari frequenza di falsi allarmi, assenza di incidenti cloud reali annotati.
Nessuna promessa di prevenzione delle spese o superiorità sui servizi AWS.

Fonti: [allarmi](validation/results/cloud_extended_anomalies.csv),
[ritardi](validation/results/cloud_extended_delays.csv),
[previsioni](validation/results/cloud_extended_forecasts.csv).

### SolarCast — produzione fotovoltaica

**Domanda:** il valore del modello cambia se interessa l'energia giornaliera
oppure la sua distribuzione nelle ore?

Anno 2023, una località, produzione simulata da PVGIS e meteo storico futuro
conosciuto a posteriori. Confronto esplorativo con regressioni su radiazione,
nuvolosità e temperatura, variando la lunghezza dello storico.

- Rispetto alla regressione con tre covariate e 30 giorni di training,
  Timestral ha un errore sul totale giornaliero **10,5% maggiore**:
  0,5647 contro 0,5111 kWh/kWp.
- Sul profilo orario diurno l'errore è invece **23,0% inferiore**:
  0,06647 contro 0,08638 nelle unità orarie normalizzate del dataset.
- La configurazione della regressione è emersa in un'analisi esplorativa;
  occorre confermarla su un periodo nuovo. A parità anche di storico lungo,
  Timestral supera la regressione su entrambe le metriche aggregate.

**Conclusione pubblicabile:** il modello è un candidato interessante per la
forma del profilo orario. Il test non dimostra ancora un vantaggio nella
programmazione dei consumi o nel risparmio in bolletta.

**Limiti da mostrare insieme ai numeri:** target simulato, meteo oracle,
un solo anno e una sola località, nessun carico domestico/tariffa simulato.

Fonti: [regressioni](validation/results/solar_matched_summary.csv),
[Timestral e baseline originali](solarcast/results/pvgis-5M/summary.csv),
[confronti per orizzonte](validation/results/solar_matched_paired.csv).

### Capacity Planner — dal traffico reale alla capacità

**Domanda:** prevedere meglio il traffico permette anche di predisporre meno
risorse, mantenendo coperta la domanda?

#### A cosa serve, in parole semplici

Un responsabile di rete deve preparare la capacità per il giorno seguente.
Se ne predispone troppa, lascia risorse inutilizzate; se ne predispone poca,
in alcune ore il traffico può superare quanto il sistema riesce a sostenere.
Capacity Planner permette di vedere il traffico previsto nelle prossime 24 ore,
provare un piano di capacità e confrontarlo con ciò che è realmente accaduto.

La dashboard comprende confronto di nove metodi, replay di dodici istituzioni
CESNET, piano orario, capacità per modulo, margine di sicurezza, tempo di
attivazione, costo ipotetico, esportazione CSV e risultati della ricerca.
Le previsioni dei replay sono salvate: cambiare i parametri della simulazione
non riscrive il benchmark. La demo sintetica può eseguire anche inferenze
Timestral reali su CPU. L'applicazione non attiva o spegne risorse reali.

**Il vantaggio dello strumento oggi è rendere confrontabili le alternative:**
mostra dove si sbaglia la previsione, dove la capacità non basta e quando un
piano più piccolo comporta più domanda scoperta. È un laboratorio di verifica
e un supporto alla pianificazione; il risparmio aziendale resta da dimostrare.

#### Dati reali, controlli e parte simulata

La fonte è **CESNET-TimeSeries24**, un dataset pubblico di traffico di rete
misurato, distribuito con licenza CC-BY-4.0. Il target è il numero di byte
osservati in ogni ora, convertito in Mbit/s medi. Non misura CPU, richieste
HTTP, picchi istantanei o qualità del servizio.

Prima del confronto sono stati eseguiti questi controlli:

- Verifica SHA-256 del file scaricato e registrazione della provenienza.
- Controllo degli identificativi temporali, dei duplicati e dei valori non
  validi; ricostruzione della griglia oraria UTC per individuare le assenze.
- Conservazione dei dati mancanti: un'ora senza osservazioni non diventa
  automaticamente un'ora di traffico zero. Il solo storico necessario alla
  previsione viene riempito usando informazioni precedenti.
- Scelta delle istituzioni sul solo periodo iniziale, senza cercare quelle
  sulle quali l'AI avrebbe ottenuto il risultato migliore.
- Separazione fra passato disponibile al modello e futuro da prevedere.

Questi controlli rendono l'elaborazione verificabile. **Non certificano
l'assenza di errori negli strumenti di misura originali**, né che dodici
istituzioni rappresentino qualsiasi infrastruttura. Non possiamo inoltre
escludere che dati pubblici fossero presenti nel pretraining del modello.

**Il traffico è reale; capacità e costi sono simulati.** Il throughput di un
modulo è un'ipotesi fissata dallo storico, non la prestazione misurata di un
server. Non abbiamo fatture, latenze, code o pacchetti persi osservati.

#### Come è stato impostato il confronto

Sono state estratte dodici istituzioni, con seed fissato, fra le 276 che
superavano i controlli di copertura e attività sullo storico iniziale.
Il training iniziale comprende 5.352 ore, dal 9 ottobre 2023 al 18 maggio 2024.
Ogni previsione utilizza al massimo le ultime dodici settimane, per tutti
i modelli. I periodi successivi, in UTC, hanno funzioni distinte:

| Periodo | Funzione |
|---|---|
| 19 maggio–1 giugno 2024, 14 giorni | Calibrare il margine contro gli errori di previsione |
| 2–15 giugno, 14 giorni | Scegliere margine, modello AI e metodo classico di confronto |
| 16 giugno–13 luglio, 28 giorni | Valutare le scelte congelate su un periodo finale separato |

Il test finale contiene **335 coppie istituzione/giorno complete su 336**.
Un giorno incompleto è escluso per tutti i metodi. Complessivamente sono
state calcolate 6.048 previsioni giornaliere di 24 ore, includendo calibrazione,
selezione e test. Non sono 6.048 osservazioni indipendenti.

Timestral 5M e 28M sono confrontati con ultimo valore, giorno precedente,
settimana precedente, media di quattro settimane, ETS, MSTL e regressione
con calendario. Anche i metodi classici ricevono margini calibrati con la
stessa regola. Modelli e criteri non sono stati cambiati dopo aver visto il test.

#### Vince l'AI oppure il metodo classico?

**Sulla previsione del traffico, Timestral migliora il risultato nel campione.**
Il MAE, cioè la distanza media assoluta tra previsione e osservazione, è
1,7968 Mbit/s per il 28M contro 2,2684 per ETS: **20,79% di errore in meno**.
ETS era il metodo classico scelto prima del test. Il MAE medio è inferiore
a ETS in tutte le dodici istituzioni.

L'analisi statistica secondaria dà un intervallo al 95% **[15,05%; 26,58%]**
per quella riduzione. Il ricampionamento mantiene accoppiati i confronti e
usa blocchi settimanali per tenere conto della dipendenza temporale. Questo
misura l'incertezza sul campione; non garantisce lo stesso vantaggio altrove.

Il MASE, un errore rapportato alla variabilità stagionale dello storico,
è 0,5426 per 28M contro 0,7301 per ETS: riduzione del 25,68%, intervallo
[16,42%; 34,79%]. La migliore baseline classica per MASE nel test è MSTL,
0,7171: la riduzione rispetto a questa è circa il 24,3%, confronto descrittivo.
Il 5M è molto vicino al 28M per MAE: non abbiamo dimostrato che la taglia
maggiore produca un beneficio pratico rilevante rispetto alla più piccola.

**Sul piano di capacità, il vantaggio dell'AI non è dimostrato.** La tabella
conserva tutti i metodi, inclusi quelli classici che danno piani migliori.

| Metodo | MAE, Mbit/s ↓ | Moduli-ora simulati | Domanda normalizzata non coperta ↓ |
|---|---:|---:|---:|
| Ultimo valore | 3,1430 | 148.825 | 2,158% |
| Giorno precedente | 2,7295 | 147.238 | 2,282% |
| Settimana precedente | 2,9699 | 138.030 | 1,305% |
| Media di quattro settimane | 2,6626 | 128.721 | 1,349% |
| ETS, riferimento selezionato | 2,2684 | 142.798 | 1,835% |
| MSTL | 3,2595 | 136.162 | 1,469% |
| Regressione con calendario | 2,8291 | 133.396 | 2,247% |
| Timestral 5M | 1,8037 | 132.651 | 2,080% |
| Timestral 28M, AI selezionata | 1,7968 | 133.800 | 2,060% |

Un modulo attivo per dieci ore corrisponde a dieci moduli-ora. Questo misura
la capacità simulata, non euro spesi. Il deficit misura domanda oltre la
capacità disponibile, normalizzata per il modulo di ogni istituzione:
non equivale a pacchetti persi o violazioni di un contratto di servizio.

Rispetto a ETS, il piano AI usa il **6,30% di capacità in meno**, intervallo
**[3,46%; 9,86%]**, ma lascia più domanda scoperta: **2,060% contro 1,835%**.
La differenza è +0,224 punti percentuali, intervallo [−0,031; +0,905].
Non è corretto presentare quel 6,30% come risparmio a pari servizio.
La media di quattro settimane usa invece meno capacità dell'AI e ha minor
deficit nel simulatore, pur avendo una previsione mediamente meno precisa.

Il criterio iniziale richiedeva almeno il 10% di capacità in meno, deficit
entro l'1% e un confronto statistico che limitasse il peggioramento del
deficit a +0,2 punti percentuali. **Il criterio non è soddisfatto.** Nessun
metodo rispettava l'1% già sul periodo di selezione: il confronto finale
serve quindi alla diagnosi, non costituisce un via libera operativo.

Anche l'incertezza richiede attenzione: gli intervalli calibrati nominalmente
all'80% coprono il 71,84% dei target per 28M e il 76,67% per ETS nel test.
La copertura dichiarata dal metodo non va interpretata come garanzia futura.

#### Cosa abbiamo verificato e cosa manca

La verifica matematica esplicita come previsione e margine diventano capacità,
come si conteggiano risorse e deficit e come si conserva la quantità totale
fra domanda coperta e capacità inattiva. L'evidenza del vantaggio deriva dal
test e dagli intervalli statistici, non da un teorema di superiorità dell'AI.

Sono passati **19 test Python, tre test browser desktop/mobile e due verifiche
API con inferenza reale 5M/28M**. Controllate anche esportazione CSV, gestione
degli errori, tema e visualizzazione dei replay. Il benchmark ha impiegato
488 secondi con limite di 2 GiB e una CPU, senza rete per l'inferenza.
La RAM host libera minima campionata durante preparazione/test/benchmark è
stata 7,06 GiB; gli otto servizi preesistenti sono rimasti invariati.
I test software dimostrano il funzionamento delle parti verificate, non il ROI.

Per un impiego reale ha senso affiancare il previsore al metodo corrente e
misurarlo sul traffico del servizio. Per sostituire il dimensionamento
occorrono throughput reale per risorsa, costi, tempi di attivazione, vincoli
di servizio e un nuovo periodo di verifica. Margini adattivi e correzioni
reattive sono possibili sviluppi: non sono risultati già ottenuti.

I limiti rimangono dodici istituzioni, quattro settimane finali, medie orarie,
possibile presenza dei dati nel pretraining e assenza di una prova live.
L'evidenza privata di Coralogix che aveva motivato l'idea resta distinta dal
nostro esperimento pubblico su CESNET: non ne abbiamo replicato il protocollo.

**Testo breve pronto per la pagina:**

> Ho realizzato Capacity Planner per verificare se una previsione AI migliore
> può aiutare a pianificare la capacità di rete. La dashboard confronta nove
> metodi su traffico reale, con controlli sui dati e un test finale separato.
> Su dodici istituzioni, Timestral 28M riduce l'errore medio di previsione del
> 20,8% rispetto a ETS. Il piano di capacità costruito su quelle previsioni
> non supera però l'obiettivo operativo: usa meno risorse del riferimento,
> ma lascia più domanda scoperta. Il progetto mostra un vantaggio misurato
> nella previsione e rende esplicito il lavoro necessario per trasformarlo
> in risparmio. È uno strumento per confrontare e verificare decisioni, con
> risultati favorevoli e sfavorevoli consultabili nella stessa interfaccia.

Fonti e artefatti: [ricerca completa](capacityplanner/docs/RESEARCH.md),
[formule](capacityplanner/docs/MATHEMATICS.md),
[protocollo](capacityplanner/docs/PROTOCOL.md),
[controlli e selezione dei dati](capacityplanner/results/cesnet/data_selection.json),
[risultati dei nove metodi](capacityplanner/results/cesnet/summary.csv),
[analisi statistica secondaria](capacityplanner/results/cesnet/secondary_analysis.json),
[grafico del confronto](capacityplanner/results/cesnet/comparison.svg).

## Competenze dimostrate

- Pipeline di dati, API Python e interfacce React/TypeScript utilizzabili.
- Integrazione di Timestral con inferenza reale su CPU e baseline esplicite.
- Backtest temporali, controlli di leakage e confronto delle politiche decisionali.
- Riconoscimento dei limiti delle metriche e pubblicazione dei risultati negativi.
- Esecuzione isolata con limiti di risorse e controlli di riproducibilità.

La validazione software ha prodotto **194 test passati**, con sei test di
integrazione esclusi da quella suite e inferenze reali eseguite nei benchmark
separati. I test software verificano il funzionamento del codice: non sono
una prova del vantaggio economico del modello. Capacity Planner aggiunge
19 test Python, tre test browser desktop/mobile e verifiche API con 5M/28M
reali. Il benchmark conserva anche il mancato raggiungimento dell'obiettivo.

## Messaggio finale per la pagina

Timestral mostra capacità utili nei nostri confronti. Il lavoro applicativo
consiste nel collegare quelle capacità alla decisione giusta: stimare un profilo
orario, prevedere un volume cumulato o riconoscere un incidente richiedono
valutazioni diverse. Il passo successivo è correggere e verificare questo
collegamento, poi misurare i risultati su dati reali nuovi.

La [pianificazione della capacità](capacityplanner/README.md) è ora un quarto
progetto realizzato e verificato su dati reali. L'evidenza esterna che aveva
motivato l'idea resta distinta dai nostri risultati. Il vantaggio previsionale
è stato misurato; il vantaggio operativo del piano rimane non dimostrato.

## Indicazioni editoriali

- Mostrare sempre baseline, metrica, orizzonte e natura dei dati accanto alla
  percentuale; non usare il solo claim «AI più accurata del 17%».
- Non presentare minori vendite perse nella vecchia simulazione come risparmio:
  le politiche di scorta erano differenti.
- Etichettare le applicazioni come demo/portfolio; non dichiararle prodotti
  validati in produzione.
- Conservare i risultati contrastanti: sono parte centrale del caso di studio.
- Collegare il [rapporto completo](validation/RESULTS.md) e il
  [protocollo riproducibile](validation/README.md).
- Se si trasformano i CSV in grafici: valori più bassi sono migliori per gli
  errori; evitare una classifica unica che mescoli energia, allarmi e inventario.
