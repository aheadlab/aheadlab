# Idea di ricerca: Capacity Planner per servizi e code di elaborazione

Proposta originaria del 5 novembre 2026, ora implementata in
[Capacity Planner](../capacityplanner/README.md). Il benchmark pubblico è stato
eseguito il 6 novembre: vantaggio previsionale misurato, criterio operativo non
soddisfatto. [Risultati completi](../capacityplanner/docs/RESEARCH.md).
La proposta qui sotto conserva la motivazione iniziale; il caso realizzato usa
traffico di rete CESNET, non richieste di una coda. Nessun autoscaling attivato.

## Problema concreto

Un operatore gestisce servizi con traffico che cambia durante il giorno e la
settimana. Deve pianificare capacità per il giorno seguente: quante risorse
rendere disponibili nelle diverse fasce orarie, conservando un margine contro
gli aumenti di domanda e limitando risorse inutilizzate.

Il primo bersaglio proposto è il volume di richieste o messaggi in ingresso a
una coda. È più vicino a una domanda esterna di quanto lo sia l'utilizzo CPU
percentuale, che cambia anche quando si modifica la capacità assegnata.

Esempio di interfaccia: curva delle prossime 24 ore, intervalli, capacità
attualmente disponibile, finestre in cui potrebbe non bastare e confronto
storico con la baseline. Le raccomandazioni rimangono consultive nel prototipo.

## Evidenza esterna che motiva la scelta

Coralogix pubblica un test su 19 serie di telemetria produttiva. MASE aggregato:

| Modello | 24 ore | 7 giorni |
|---|---:|---:|
| Timestral 5M | 0,358 | 0,647 |
| Timestral 28M | 0,337 | 0,605 |
| MSTL | 0,497 | 0,737 |

Per 28M la riduzione rispetto a MSTL è circa 32,2% e 17,9%, calcolata sui punteggi
pubblicati. Dati privati: non replicati qui. Il confronto limita AutoARIMA a
quattro settimane; AutoETS seleziona modelli non stagionali. La metrica usa
media geometrica e un floor; non è una percentuale di risparmio.

Fonte primaria, autore dell'esperimento:
[Coralogix — Timestral on Production Data](https://benchmarks.coralogix.com/timestral-benchmarks).

Questa evidenza sostiene una candidatura concreta alla previsione del carico.
La nostra applicazione alla pianificazione delle risorse è una proposta da
validare: quel benchmark non prova il risparmio del nostro sistema.

## Perché lo sceglierei per Aheadlab

È un compito in cui l'uscita temporale del modello può essere utilizzata
direttamente: previsione oraria della domanda futura. Evita di confondere una
spesa indesiderata con un valore statisticamente inatteso. L'ipotesi è che un
previsore trasferibile sia utile su servizi eterogenei, con cicli combinati e
storici sufficienti; il confronto deve includere modelli classici ben configurati.

Il passaggio da domanda a risorse resta un secondo modello, da dichiarare:
throughput misurato per worker, tempi di avvio, vincoli di concorrenza e backlog.
Una soglia di CPU non è da sola una misura di domanda o di qualità del servizio.

## Esperimento proposto, prima di costruire un quarto frontend

1. Ottenere 12–16 settimane di serie orarie reali e un successivo periodo finale
   non usato per selezionare parametri. Richieste/ora o messaggi/ora come target;
   convertire i contatori cumulativi in incrementi gestendo reset e buchi.
   La durata è una scelta proposta, non un requisito universale di Timestral.
2. In alternativa, scegliere una traccia pubblica dalla raccolta ufficiale
   [Microsoft Azure Traces](https://github.com/Azure/AzurePublicDataset) o
   [Alibaba Cluster Trace](https://github.com/alibaba/clusterdata). Verificare
   durata, licenza, significato del target e dimensione prima del download.
   Una traccia troppo corta non sostiene conclusioni sulla stagionalità settimanale.
3. Baseline: ultimo valore, stesso giorno precedente, stessa settimana,
   ETS stagionale, MSTL con stagionalità 24/168, regressione con calendario e
   lag; una baseline boosted trees se il campione consente un fit sensato.
   Tuning solo su validation e budget computazionali dichiarati.
4. Provare 5M e 28M con snapshot fissati. Identiche origini e informazioni;
   imputazione calcolata usando solo il passato, nessun riempimento che attraversi
   il cutoff. Nessuna covariata futura non disponibile al momento della previsione.
5. Valutare prima MAE/MASE e pinball loss, bias, copertura e ampiezza degli
   intervalli per servizio e fascia. Calibrare intervalli anche per le baseline;
   evitare vantaggi derivanti da protezioni assegnate solo all'AI.
6. Simulare la stessa politica per tutti: capacità discreta, ritardo di avvio,
   throughput, coda iniziale e costo delle risorse identici. Misurare capacità-ora
   e domanda non servita/ritardo. Senza tempi di servizio misurati è una
   simulazione di deficit di capacità, non una prova di latenza o rispetto SLA.
7. Confrontare i costi a pari limite di disservizio e il disservizio a pari
   budget. Conservare un periodo finale cieco, includere baseline senza forecast
   e misurare anche costo di inferenza e lavoro di configurazione.

## Criterio di successo proposto

Prima del test finale, concordare una soglia pratica, per esempio almeno il
10% di capacità-ora in meno a parità di disservizio simulato. È un criterio
progettuale da fissare in anticipo, non un risultato atteso né una percentuale
derivata dai benchmark. Se migliora soltanto il MAE, pubblicare il vantaggio
previsionale senza dichiarare beneficio operativo.

## Risorse e rapporto con i progetti esistenti

Esperimenti separati in `validation/`, sotto gli stessi limiti dei job precedenti;
nuovo controllo della memoria prima di eseguire. Non leggere dati applicativi
sensibili o installare collector sui servizi produttivi come effetto implicito
di questa proposta. Per una raccolta locale va prima definito quali metriche
usare e l'impatto del collector. Gli uptime dei container non equivalgono a
storico delle metriche già disponibile.

CloudGuard resta la demo sui costi. Capacity Planner può iniziare come notebook
o report riproducibile; una nuova interfaccia ha senso dopo un risultato locale.

## Altra evidenza utile, senza cambiare la proposta principale

Superlinear riporta Timestral 28M migliore di ETS del 5,9% su Walmart e del 5,5%
su FreshRetailNet in quantile loss, su tre periodi. È un ulteriore confronto
previsionale favorevole, non una misura di profitto. Codice su richiesta;
possibile sovrapposizione con i dati di training non esclusa dagli autori.
[Studio originale](https://superlinear.eu/insights/articles/timestral-vs-timesfm-ai-forecasting-grocery-benchmark).
