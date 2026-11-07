# Validazione esplorativa — 5 novembre 2026

## Esito

I tre esempi frontend rimangono intatti. La validazione rafforza la credibilità
del portfolio come confronto sperimentale, ma NON dimostra una superiorità
operativa generale di Timestral. Sono presenti vantaggi previsionali reali nei
campioni esaminati; la loro conversione in beneficio operativo rimane da provare.
In particolare, un MAE giornaliero migliore non implica una migliore stima del
volume da riordinare.

### Interpretazione: cosa abbiamo validato e cosa va ancora progettato

I risultati non giustificano la conclusione «Timestral non serve». La riduzione
del MAE retail e dell'errore orario solare è misurata. Il giudizio sul prodotto
dipende anche dall'uso delle uscite del modello e dalla funzione di costo scelta.

StockSense usa mediane puntuali per costruire un totale: quella somma non è in
generale la media né la mediana della domanda cumulata. Questo disallineamento
contribuisce a spiegare perché un modello competitivo sul MAE giornaliero possa
essere meno adatto al riordino nella configurazione provata. Non abbiamo isolato
causalmente quanto della differenza dipenda da questa scelta e quanto dal modello.
Una diversa previsione del totale o una politica calibrata può essere studiata;
non è una correzione con successo garantito. In particolare, non basta sommare
quantili marginali o farne la media per ottenere una distribuzione del totale.

CloudGuard aggiunge una regola p99 a un previsore: la capacità di prevedere non
equivale a conoscere l'intento di una modifica infrastrutturale. Il verdetto
negativo sugli allarmi vale per quel rilevatore e quegli scenari, non per ogni
possibile uso del modello in ambito cloud.

Il costo di configurazione, riaddestramento e manutenzione su molte serie è
un'altra possibile dimensione di vantaggio, non ancora misurata da noi. I
modelli sono stati impiegati senza nostro fine-tuning; questo non certifica
l'assenza dei dataset pubblici dal loro addestramento originale.

Nuova direzione motivata da evidenze esterne: [capacity planning dei servizi](IDEA_CAPACITY_PLANNING.md).
La proposta non modifica i tre esempi frontend né aggiunge risultati locali.

Codice applicativo esaminato: commit `d7a0921`. Script riproducibili e protocollo
in [README.md](README.md), piano in [VALIDAZIONE.md](../VALIDAZIONE.md).
I dati erano già stati esaminati: tutti i nuovi confronti sono esplorativi,
non un holdout finale indipendente. Nessun costo o risparmio economico è inventato.

## Risorse, integrità e verifiche

- Prima dei job: circa 9,7 GiB liberi su Windows; Docker 23,47 GiB totali,
  Linux MemAvailable circa 20,94 GiB, comprensivi di cache recuperabile.
- Un container temporaneo alla volta: 2 GiB, 1 CPU, swap aggiuntivo zero,
  rete disabilitata, repository/cache modelli read-only. Nessuna porta esposta.
- Minimo RAM host disponibile campionato durante i job: **9,01 GiB**.
  Campionamento ogni 5 secondi, non una misura continua del picco.
- Otto servizi preesistenti invariati nei confronti prima/dopo: stessi ID,
  orari di avvio, contatori di restart, stato e healthcheck ove presente.
- Nessun arresto, riavvio, rebuild o modifica delle applicazioni/Compose.
- Suite esistenti: CloudGuard **63 passati + 2 saltati**, StockSense **73 + 2**,
  SolarCast **58 + 2**: **194 passati**, 6 integrazioni modello escluse dalle suite.
  Le inferenze reali 5M sono state eseguite separatamente nei benchmark.
- Verifiche degli artefatti: 1600 score SKU/fold, 108000 righe di inventario,
  domanda identica, conservazione delle giacenze con lead time, completezza
  degli output solari e cloud. `python validation/check_results.py`: PASS.
- I 400 MAE originali 5M sono riprodotti con differenza assoluta massima
  **0,000488**; non si dichiara identità bit-per-bit fra configurazioni numeriche.
- Snapshot 5M fissato: `bdd20cfc15a3fea0e4cb5ccef37f8d3ca7aa335f`.
  Hash Excel/parquet in `results/stock_metadata.json`; ambiente e hash sorgenti
  nelle registrazioni `*_environment.json`. Queste ultime descrivono le fasi
  audit/solar/cloud; lo stock è stato avviato prima dell'aggiunta del registratore.

## StockSense: qualità puntuale e domanda cumulata danno verdetti diversi

50 SKU selezionati solo sul prefisso; otto finestre da 30 giorni. Stesso clipping
sul training, nessuna modifica dei target. Mediana mobile e Croston-SBA aggiunti.

| Metodo | MAE giornaliero medio | Bias medio (previsto − reale) | Errore assoluto sul totale 30 giorni |
|---|---:|---:|---:|
| Timestral 5M | **41,318** | −25,263 | 789,933 |
| AutoETS | 49,692 | **−0,757** | **560,826** |
| Mediana mobile 28 giorni | 45,233 | −30,153 | 919,675 |
| Croston-SBA | 53,237 | −3,801 | 616,295 |

L'AI migliora il MAE del 16,9% rispetto ad AutoETS e dell'8,7% rispetto alla
mediana mobile. Ma l'errore sul volume totale dei 30 giorni è **40,8% peggiore
di AutoETS**. La mediana è adatta alla perdita assoluta giornaliera, mentre la
somma delle mediane non è automaticamente la domanda media o la mediana del
totale. La sottostima osservata richiede una correzione/calibrazione per il riordino.

Bootstrap esplorativo con ricampionamento dei 50 SKU (tutti i fold di uno SKU
restano insieme), 2000 repliche: vantaggio MAE su AutoETS 8,37 unità/giorno,
intervallo 95% [6,12; 10,96]. Sul totale a 30 giorni il vantaggio cambia segno:
−229,11 unità, intervallo [−311,09; −150,22]. Sono intervalli condizionati a questo
negozio: non eliminano shock comuni né provano generalizzazione ad altri retail.

Fonti: [accuratezza](results/stock_new_accuracy.csv),
[confronti accoppiati](results/stock_new_paired.csv),
[score completi](results/stock_new_scores.csv).

### Inventario con la stessa regola per tutti

180 giorni; lead time 14; revisione ogni 7; medesime giacenze iniziali. Scorta
aggiuntiva derivata da sei errori cumulati di 21 giorni prima del test, congelata
durante la simulazione. Nessun uso dei p90 marginali dell'AI. I livelli indicano
quantili empirici della calibrazione, NON livelli di servizio garantiti.

| Metodo | Livello calibrazione | Giacenza media in pezzi per SKU-giorno | Unità perse totali | Fill rate |
|---|---:|---:|---:|---:|
| 5M | 0,5 | 383,73 | 122.666 | 73,99% |
| AutoETS | 0,5 | 445,20 | 107.197 | 77,27% |
| 5M | 0,8 | 574,08 | 82.841 | 82,43% |
| AutoETS | 0,8 | 618,43 | 78.796 | 83,29% |
| 5M | 0,9 | 739,44 | 61.667 | 86,92% |
| AutoETS | 0,9 | 772,93 | 61.117 | 87,04% |

Al livello 0,9 l'AI impiega il 4,3% di merce in meno e perde lo 0,9% di unità in
più. I punti 5M e AutoETS non si dominano: non c'è una vittoria netta. Nei dodici
punti esaminati tutti i punti della mediana mobile sono dominati; Croston-SBA
con scorta elevata ottiene meno perdite, pagando maggiore giacenza.

È un confronto a pari REGOLA, non ancora a pari capitale o pari servizio. Sei
residui sono pochi; il periodo e i lead time sono fissi. Le unità di prodotti
diversi non hanno lo stesso costo. Non si deduce un ROI da questo prospetto.
Domanda basata sulle transazioni UCI, non sulla domanda latente in presenza di
stockout; inventario sempre simulato. Nessun costo di ordine, obsolescenza,
deposito o margine perso è disponibile.

Fonte: [tutti i dodici scenari](results/stock_equal_policy_summary.csv).
Il ledger completo resta locale per riprodurre i controlli, escluso da Git.

## CloudGuard: superiorità dipendente da scenario e orizzonte

Nel vecchio campione entrambi rilevano tutti gli eventi già al primo giorno:
il minor recall giornaliero dell'AI non equivaleva a un ritardo del primo allarme.
Fonte: [ritardi originali](results/cloud_event_delays.csv).

Nuovo stress test: tre seed, tre servizi per seed, 360 giorni, picchi 1,7x di
tre giorni, derive graduali dal 5 al 45% in 21 giorni e aumento pianificato
permanente del 25%. I rilevatori non ricevono l'informazione sul cambio pianificato.
Sono scenari sintetici progettati dopo aver osservato il benchmark originale.

| Metodo | Picchi rilevati | Derive rilevate | Falsi allarmi (servizio-giorni) |
|---|---:|---:|---:|
| Timestral 5M | 9/9 | 1/9 | 12 |
| Media + 3 sigma | 9/9 | 5/9 | 11 |

Tutti i picchi sono rilevati al giorno zero. L'unica deriva rilevata dall'AI è
segnalata dopo 19 giorni; la regola segnala le cinque derive dopo 6–20 giorni.
Entrambe sono deboli sulle derive. Questi risultati non identificano un vincitore
universale; indicano che il rilevatore 5M+p99 attuale non giustifica la sostituzione
della regola semplice su questi scenari. Le soglie non sono calibrate a pari FPR.

| Metodo | MAE 7 giorni | MAE 30 giorni |
|---|---:|---:|
| Timestral 5M | **2,9358** | 4,8951 |
| Copia settimana | 3,7675 | **4,1646** |
| Media mobile | 3,9671 | 5,1888 |

Il vantaggio previsionale cambia segno aumentando l'orizzonte. Il modello può
incorporare una deriva nello storico senza interpretarla come incidente:
prevedere il prossimo valore e decidere se sia accettabile sono problemi distinti.

Fonti: [allarmi](results/cloud_extended_anomalies.csv),
[ritardi](results/cloud_extended_delays.csv),
[previsioni](results/cloud_extended_forecasts.csv),
[protocollo](results/cloud_metadata.json).

## SolarCast: vantaggio orario, forte baseline sul totale giornaliero

Stesso anno 2023, località, target PVGIS e meteo oracle originali. Nessuna nuova
inferenza AI: rianalisi delle 728 coppie origine/giorno pubblicate. Le regressioni
sono state realmente ricalcolate sui dati locali. La baseline originale è stata
riprodotta numericamente. Analisi fattoriale esplorativa di storico e covariate:

| Metodo | MAE energia giornaliera kWh/kWp | MAE orario diurno |
|---|---:|---:|
| Timestral B, storico fino a 8784 ore | 0,5647 | **0,06647** |
| Radiazione, 720 ore (originale) | 0,5440 | 0,09130 |
| Tre covariate, 720 ore | **0,5111** | 0,08638 |
| Radiazione, 8784 ore | 0,8592 | 0,10390 |
| Tre covariate, 8784 ore | 0,6168 | 0,09507 |

Rispetto alla regressione a tre covariate e 720 ore, l'AI è circa il 10,5%
peggiore sul totale giornaliero e il 23,0% migliore sul profilo orario. Rispetto
alla regressione con identici storico e covariate, l'AI vince su entrambe le
metriche aggregate. Uno storico maggiore non garantisce una regressione migliore;
la migliore configurazione osservata richiede un nuovo periodo per essere confermata.

La divisione per lead time aggiunge una distinzione: contro la regressione
originale, l'AI ha un vantaggio medio sull'energia del primo giorno di 0,0936
kWh/kWp; sul secondo uno svantaggio di 0,1349. Intervalli esplorativi bootstrap
a blocchi di 28 origini: [0,0293; 0,1580] e [−0,2104; −0,0549]. Le origini
sovrapposte non sono trattate come 728 giornate indipendenti. L'anno e l'impianto
restano unici; la sensibilità usa anche blocchi di 7 origini.

Fonti: [regressioni](results/solar_matched_summary.csv),
[confronti delle quattro configurazioni](results/solar_matched_paired.csv),
[confronto originale per lead time](results/solar_existing_paired.csv).

Questi risultati non validano fasce di autoconsumo, calibrazione degli intervalli
diurni o risparmio in bolletta. Il meteo conosciuto a posteriori e il target
simulato continuano a impedire una conclusione operativa.

## Decisioni e lavoro residuo

1. Mantenere i tre frontend come esempi e presentare questi risultati in un
   documento di ricerca separato. Nessuna modifica silenziosa ai report demo.
2. StockSense: conservare Timestral come candidato, ma valutare domanda cumulata
   e calibrazione più ampia. Provare pari budget/servizio e costi per SKU su un
   secondo dataset con periodo finale intatto. Nessuna ragione emersa per
   passare automaticamente a 209M.
3. CloudGuard: conservare la baseline come riferimento. Prossime prove: stessa
   frequenza di falsi allarmi, errori sulla fattura di fine mese, dati reali con
   incidenti e cambi pianificati annotati. Queste prove non sono state eseguite.
4. SolarCast: usare una baseline forte e separare giorno 1/2. Servono produzione
   misurata, meteo con timestamp di emissione, validazione diurna degli intervalli
   e carichi/tariffe per misurare autoconsumo. Queste prove non sono state eseguite.
5. Nessuna stima di vantaggio commerciale finché non esistono costi e risultati
   prospettici. La validazione con dati già disponibili è conclusa per questa
   fase; la validazione sul campo rimane aperta.
