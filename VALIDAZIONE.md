# Piano di validazione scientifica

Avvio: 5 novembre 2026. Commit applicativo di riferimento: d7a0921.

## Vincoli e risorse

I tre prodotti sono esempi frontend: nessuna modifica a UI, API, logica runtime,
immagini o configurazione dei servizi attivi. Esperimenti in `validation/`;
risultati nuovi separati dai report già usati dalle demo. Nessun arresto o riavvio
di container esistenti. Nessuna pubblicazione automatica.

Controllo iniziale: Windows 31,3 GiB totali, 9,7 GiB liberi; Docker 23,47 GiB;
Linux MemAvailable circa 20,94 GiB (include cache recuperabile). Otto container
attivi, circa 1,4 GiB complessivi nel campione docker stats. Questi valori sono
istantanee, non garanzie sulla disponibilità futura.

Esecuzione: un solo container temporaneo, 2 GiB RAM, swap aggiuntivo disabilitato,
1 CPU, duecentocinquantasei processi massimi, rete disabilitata. Repository e
cache modelli in sola lettura; scrittura limitata alla cartella risultati e al
filesystem temporaneo del container. Controllare memoria host e stato dei
servizi durante e dopo i job. Se il margine si riduce, interrompere esclusivamente
il job di validazione. Non scaricare modelli più grandi per questa fase.

## Protocollo deciso prima dei nuovi esperimenti

I periodi esistenti sono già stati esaminati: questa è una validazione esplorativa,
non un nuovo test cieco. Non selezionare parametri sul risultato finale.

1. Eseguire le suite esistenti su copie isolate delle immagini, usando il codice
   del workspace in sola lettura. Distinguere test software da evidenza scientifica.
2. StockSense: riprodurre il benchmark 5M su 50 SKU e otto finestre, aggiungere
   mediana mobile e Croston-SBA; confrontare MAE e risultati per SKU/finestra.
   Riordino: stessa politica per tutti, con errori cumulati di training per
   costruire la scorta, livelli di quantile fissati 0,5/0,8/0,9; stessa giacenza
   iniziale, lead time 14, revisione 7. Analizzare vendite perse rispetto a
   giacenza; non attribuire un ROI senza costi economici forniti. La calibrazione
   usa sei finestre da 21 giorni precedenti l'inizio della simulazione ed è
   congelata durante il test. È piccola: non promette copertura nominale.
3. CloudGuard: quantificare vantaggi per servizio/orizzonte, dipendenza fra fold,
   ritardo del primo allarme ed eventi; estendere a più seed e cambiamenti
   graduali/legittimi prima di trarre conclusioni operative.
4. SolarCast: distinguere giorno 1/2 e stagioni; intervalli sul confronto tramite
   ricampionamento temporale a blocchi. Aggiungere regressione con stesse
   covariate e storico dell'AI. Nessun risultato oracle è chiamato operativo.
5. Pubblicare risultati favorevoli e sfavorevoli, hash dei dati e revisioni dei
   pesi, comandi, limiti e stato effettivo di ciascun esperimento.

## Criteri di decisione

- Previsione: MAE inferiore alla migliore baseline rilevante; riportare dimensione
  e stabilità del vantaggio, senza contare righe correlate come indipendenti.
- Inventario: confrontare la frontiera giacenza/vendite perse; dominanza solo se
  entrambe non peggiorano. Nessun equivalente fra giacenza in pezzi e capitale.
- Allarmi: recall per evento, ritardo, falsi allarmi e persistenza; recall per
  giorno da solo non decide l'utilità.
- Solare: energia giornaliera e profilo orario distinti. Per autoconsumo serve
  successivamente una simulazione di carico/tariffe con dati misurati.

## Fase successiva dipendente da nuovi dati

Secondo dataset retail con periodo finale non esplorato; costi cloud reali con
incidenti annotati; produzione inverter e meteo archiviato per data di emissione.
Soglia economica minima da decidere sul caso concreto. Senza questi dati non è
possibile concludere che i prodotti generino risparmio in produzione.

## Stato

Prima fase completata: 194 test software passati; benchmark retail 5M riprodotto,
baseline e politiche di scorta comuni eseguite; quattro regressioni solari
ricalcolate; stress test cloud su tre seed completato. Artefatti controllati.
Otto servizi invariati; minimo RAM host campionato 9,01 GiB.

Esiti, limiti e prove ancora aperte: [validation/RESULTS.md](validation/RESULTS.md).
La fase operativa con dati reali nuovi non è completata né sostituita dai test.

## Quarto progetto: Capacity Planner

Sviluppo e benchmark completati il 6–7 novembre 2026. Nuova cartella autonoma,
dashboard React/FastAPI, Compose separato su localhost:8504; tre frontend
precedenti intatti. Protocollo fissato prima del test in
[capacityplanner/docs/PROTOCOL.md](capacityplanner/docs/PROTOCOL.md).

Dataset pubblico CESNET: dodici istituzioni selezionate sul training,
calibrazione/selezione/test separati. Confronto reale di 5M/28M con sette metodi
classici, 19 test Python passati e tre test browser passati. Verificate anche
due inferenze reali attraverso l'API finale.

Esito: MAE del 28M inferiore del 20,79% a ETS; vantaggio operativo del piano
non dimostrato (capacità −6,30%, deficit oltre soglia). Nessuna modifica del
protocollo per ottenere un esito favorevole. Analisi secondaria esplicitamente
etichettata. [Report](capacityplanner/docs/RESEARCH.md).

Durante preparazione/test/benchmark: limite 2 GiB, 1 CPU, zero rete e swap
aggiuntivo; RAM host libera minima campionata 7,06 GiB. Gli otto servizi
preesistenti sono invariati anche dopo l'avvio del quarto progetto.

Il 7 novembre, su richiesta dell'utente, Capacity Planner è stato arrestato
con `docker compose -f capacityplanner/compose.yaml stop capacityplanner`.
Dashboard e modelli caricati risiedevano nello stesso container: l'arresto
termina entrambi. Prima dello stop il container occupava circa 352 MiB;
il consumo complessivo della macchina non era attribuibile a quel solo servizio.
Gli altri otto container sono stati lasciati attivi. Dati e pesi restano su
disco per un eventuale riavvio; non rimane un processo Timestral separato
avviato da questo progetto.

## Seconda ricerca Capacity Planner, conclusa l'8 novembre 2026

Diagnosi dei picchi V1, margini aggiornati e protezione reattiva implementati
in un modulo di ricerca separato. Protocollo e hash del codice fissati prima
del test nuovo. Dati ufficiali CESNET-TimeSeries26 verificati con SHA-256;
47 ore anomale dello storico mascherate; 24 istituzioni estratte sul training,
56 giorni finali completi e 1.344 coppie istituzione/giorno.

Completate 18.144 previsioni di 24 ore, 241 configurazioni di capacità e
28 test Python (nove nuovi su causalità e simulazione). Verificati somme per
istituzione, risultati accoppiati e conservazione delle scelte primarie.
Analisi separate di componenti, dati grezzi/normalizzati e costi di esecuzione.
Nessuna modifica dei frontend; test browser della prima fase non ripetuti.

28M migliora il MAE del 35,80% rispetto a ETS, intervallo [30,04%; 41,44%].
La politica adattiva non conferma il vantaggio operativo: capacità +1,20%,
deficit 1,540% contro 1,496%, entrambi oltre soglia. La protezione reattiva
riduce il deficit, ma l'aggiornamento del margine riduce eccessivamente la
capacità. Risultati negativi conservati, nessuna scelta rifatta sul test.

Job temporanei limitati a 2 GiB e una CPU, senza rete o swap aggiuntivo.
Minimo RAM host disponibile campionato 8,39 GiB; otto servizi invariati.
Dashboard e modelli del quarto progetto restano spenti dopo i calcoli.

Prove e riproduzione: [ricerca V2](capacityplanner/docs/RESEARCH_V2.md),
[protocollo](capacityplanner/docs/PROTOCOL_V2.md),
[controlli numerici](capacityplanner/results/capacity-v2/checks.json),
[piano completato](capacityplanner/docs/WORKPLAN_V2.md).

## Quinto progetto CarbonShift, 9 novembre 2026

Nuovo caso autonomo: pianificare quattro ore di lavoro elettrico entro 96,
con identica energia e scadenza per tutti i metodi. Primo candidato scartato
(finestre di manutenzione CESNET), esplorazione conservata e protocollo
fissato prima del confronto finale. Dataset Khepri-TSFM v1.0.1, commit
fissato, checksum verificati, sei zone senza target imputati nel periodo
documentato; altre tre zone riportate separatamente.

Sul test storico separato di 176 giorni e 1.056 casi, Timestral 5M produce
emissioni attribuite inferiori dello 0,662% rispetto a GBM, selezionato sullo
sviluppo. Intervallo al 95% [0,124%; 1,202%], circa 144 g/MWh. Il criterio
primario è soddisfatto. Il controllo di 14 giorni dopo il rilascio misura
0,559%, intervallo [−0,661%; 1,797%]: inconcludente. Nessuna affermazione di
risparmio economico, emissioni marginali evitate o vantaggio in produzione.
Il GBM pubblicato non è aggiornato quotidianamente; il 2025 può sovrapporsi
al pretraining. I limiti restano accanto al risultato.

Completati 23 test Python, tre test browser desktop/mobile, controllo
TypeScript/build e API con inferenza 5M reale. Riprodotte localmente 24
previsioni pubblicate, stessa finestra in 24 casi su 24, scarto massimo
0,0000134 g/kWh. Mediana circa 87 ms, picco RSS circa 497 MiB.
Gli hash del protocollo e dei sorgenti scientifici coincidono con quelli
registrati prima del confronto. Verificate somme, selezione della baseline,
energia e scadenze; intervallo a blocchi 14 escluso per il periodo di soli
14 giorni perché degenere, senza modificarne il risultato primario.

Calcoli isolati con limite 2 GiB, una CPU, rete assente e nessuno swap
aggiuntivo. Minimo host disponibile campionato 8,51 GiB nei job scientifici.
Gli otto servizi precedenti risultano invariati. CarbonShift è stato spento
dopo i test, terminando il modello; Capacity Planner rimane spento.
I quattro progetti precedenti non sono stati modificati.

Artefatti: [ricerca](carbonshift/docs/RESEARCH.md),
[matematica](carbonshift/docs/MATHEMATICS.md),
[risultati](carbonshift/results/report.json),
[controlli](carbonshift/results/audit.json),
[registro software](carbonshift/results/software_validation.json),
[testo portfolio](PORTFOLIO_RICERCA.md).
