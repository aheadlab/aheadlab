# Protocollo V2: protezione dai picchi e valore marginale dell'AI

Fissato il 7 novembre 2026, dopo la diagnosi V1 e prima di valutare i dati V2.
È una ricerca successiva: il test 2024 è materiale di sviluppo, non una nuova
prova indipendente. Non si cambia questo protocollo in funzione dell'esito V2.

## Ipotesi motivata dalla diagnosi

Nella V1 l'85,79% del deficit del 28M proviene dall'istituzione 242; le ore
peggiori, meno dell'1% del totale, spiegano l'intero deficit. Eliminare il
ritardo alla prima ora non migliora il risultato. Ipotesi: un margine fisso
calibrato su due settimane non protegge dai picchi rari e dai cambi di scala.

Proviamo aggiornamento giornaliero del margine e protezione reattiva causale.
La stessa politica è disponibile per tutti i modelli; non basta migliorare
l'AI rispetto a se stessa, occorre superare anche le alternative classiche.

## Dati nuovi e controlli

CESNET-TimeSeries26, istituzioni, aggregazione oraria; SHA-256 ufficiale
57430eb3ea714cbeceb9b4c026010aa158b79432b7e1af291fc1cf1eebd7d49e.
Fonte: https://doi.org/10.5281/zenodo.21945629, distribuzione
https://zenodo.org/records/23283552. Si tratta della stessa rete CESNET,
con un periodo successivo: non è una validazione su un altro operatore.

- Storico per ammissibilità: 15 settembre–7 dicembre 2025, dodici settimane.
- Calibrazione degli errori: 8–21 dicembre 2025, quattordici giorni.
- Selezione dei parametri: 22 dicembre 2025–4 gennaio 2026, quattordici giorni.
- Test finale nuovo: 5 gennaio–1 marzo 2026, cinquantasei giorni UTC.
- Estrarre 24 istituzioni con seed 20261107, fra quelle con >=95% di ore
  valide e >=50% di ore positive nello storico di ammissibilità. Ordinare gli
  ID prima dell'estrazione. Non scartare istituzioni per errori o picchi futuri.
- Modulo di capacità: p95 dello stesso storico / 10, minimo 1e-9 Mbit/s.
- Identificativi temporali risolti tramite tabella timestamp; duplicati o
  valori negativi/non finiti osservati causano errore, non correzioni nascoste.
- I buchi rimangono NaN. Ore che intersecano interruzioni note del monitoraggio
  sono mancanti anche quando il file riporta zero o una somma parziale.
  Considerare anche discontinuità della griglia e transizioni DST documentate.
  Gli estremi delle interruzioni vengono arrotondati verso l'esterno all'ora;
  per DST si esclude conservativamente l'intero giorno locale Europe/Prague
  indicato dalla tabella (incluse le sue 23/25 ore). Sono controlli di qualità
  della fonte, non filtri sulle prestazioni del modello.
- Tutti i metodi vengono valutati sui medesimi giorni completi. Per ogni
  istituzione servono almeno 7 giorni completi di calibrazione e selezione,
  e 28 giorni di test; altrimenti lo studio si interrompe senza sostituire la serie.

Non si analizzano anticipatamente i valori del test: preparazione e controlli
di completezza non sono selezione per prestazione. La selezione include le
festività invernali; la differenza rispetto al test va riportata come limite.

## Previsioni e politiche

Stessi nove metodi della V1, snapshot 5M/28M e contesto di 2016 ore invariati.
Previsione giornaliera delle prossime 24 ore, storico riempito causalmente.
Ogni previsione è salvata prima di simulare le decisioni.

1. **Originale:** margine fisso dagli errori dei primi 14 giorni, quantili
   0 / 0,5 / 0,75 / 0,9 / 0,95 / 0,975 / 0,99 / 1, come nella V1.
2. **Adattiva:** margine aggiornato a inizio giornata sul quantile degli errori
   delle ultime 14 giornate concluse. Quantili 0,95 / 0,99 / 1; moltiplicatori
   1 / 1,5 / 2. Margine sempre >=0. Il livello scelto resta congelato;
   solo lo stato della regola si aggiorna con osservazioni già disponibili.
3. **Protezione reattiva facoltativa nell'adattiva:** capacità almeno pari a
   1,25 volte il massimo traffico delle ultime sei ore già disponibili con
   un'ora di provisioning. Per l'ora t si usano y[t-7:t-1], quindi al massimo
   y[t-2]: y[t-1] è noto solo all'inizio di t e arriverebbe troppo tardi.
   Candidati: protezione disattivata o attivata. Si paga tutta la capacità
   aggiuntiva; nessuna correzione istantanea che conosca il carico corrente.
4. **Controllo solo reattivo:** stesso massimo causale, fattori 1 / 1,25 /
   1,5 / 2, senza previsioni AI né margine sugli errori.
5. **Controllo fisso:** p99 dello storico iniziale, fattori 1 / 1,5 / 2,
   costante durante selezione e test. Include il costo dell'eventuale eccesso.

I piani sono interi, minimo un modulo. Il piano giornaliero mantiene la
capacità precedente nella prima ora, come V1; la protezione reattiva può
essere stata preparata dall'osservazione disponibile due ore prima. Questa
asimmetria va separata con il confronto adattivo senza protezione. Non si
simulano backlog, ramp rate, minimi contrattuali o fatturazione cloud.

Per ciascun modello e famiglia scegliere sulla selezione il piano con minori
moduli-ora fra quelli con deficit normalizzato <=1%; se nessuno è fattibile,
scegliere il minor deficit e dichiarare il fallimento del vincolo. Anche AI
e migliore alternativa classica (compresi controlli reattivo/fisso) sono
scelte sulla selezione, e mai sostituite a posteriori sul test.

## Metriche e decisioni

Primario: taglia/politica AI selezionata contro alternativa classica selezionata.
Successo richiede entrambe fattibili su selezione e test, riduzione di capacità
almeno 10%, limite inferiore dell'intervallo al 95% del risparmio >0 e limite
superiore della differenza di deficit AI-classico <=0,2 punti percentuali.
Sono gli stessi criteri primari della V1, ora su un nuovo periodo.

2000 bootstrap accoppiati di istituzioni e blocchi circolari di sette giorni,
seed 20261107. Riportare aggregati normalizzati e deficit in traffico grezzo,
distribuzione del deficit per istituzione, numero di istituzioni oltre 1% e
5%, e contributo delle peggiori ore. Nessuna esclusione dei picchi per migliorare
il verdetto. Mostrare anche MAE/MASE, copertura dei margini e capacità aggiunta.

Secondari: adattiva contro originale per ogni modello, contributo separato
di aggiornamento/protezione, AI contro controlli senza forecasting. Riportare
tradeoff espliciti, senza chiamare miglioramento una sola riduzione del deficit
ottenuta comprando capacità illimitata. Nessuna prova di euro risparmiati.

Un risultato negativo chiude questo esperimento con una conclusione motivata,
non viene sostituito da tentativi finché l'AI vince. Un nuovo esperimento
richiederebbe un'altra ipotesi e nuovi dati. I pesi possono avere visto dati
pubblici: non è disponibile una certificazione del corpus di pretraining.

## Riproducibilità e risorse

Hash di protocollo, core, simulatore e runner scientifico prima delle inferenze;
scelte e metriche della selezione scritte prima del report di test. Dati e
forecast in cache verificata, artefatti V1 intatti. Job temporanei da 2 GiB e
una CPU, rete disabilitata, stop del solo job se RAM host libera <4 GiB.
Avvio consentito solo con >=5 GiB liberi. Dashboard sempre spenta.
