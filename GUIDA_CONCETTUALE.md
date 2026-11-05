# Capire aheadlab: il modello, le applicazioni e il loro stato reale

Questa è la guida introduttiva del progetto. Non richiede conoscenze di programmazione o machine learning. Spiega **perché esistono le tre applicazioni, che cosa fa l'intelligenza artificiale e che cosa significa, concretamente, dire che funzionano**.

Per installazione e comandi usare il [README](README.md). Per prove eseguite e risultati consultare [VERIFICHE.md](VERIFICHE.md). Le spiegazioni autonome dei prodotti sono in [CloudGuard](cloudguard/docs/CONCEPTS.md), [StockSense](stocksense/docs/CONCEPTS.md) e [SolarCast](solarcast/docs/CONCEPTS.md).

## 1. La risposta più importante, prima dei dettagli

**Sono tre applicazioni locali funzionanti, non tre semplici disegni di interfaccia. Non sono ancora tre servizi integrati con la tua attività e pronti a operare autonomamente in produzione.**

Il frontend chiama un backend reale. Il backend legge dati, esegue un metodo previsionale e restituisce risultati. I grafici visualizzano quei risultati; i CSV contengono dati calcolati. Quando si seleziona Timestral e il modello è disponibile, viene eseguito il modello vero su CPU.

Tuttavia, al primo accesso si usano dati sintetici e metodi statistici di riferimento. Non si sta leggendo automaticamente la tua bolletta AWS, il tuo magazzino o il tuo inverter. Questo limite non rende finto il software: delimita ciò che è stato effettivamente costruito e verificato.

### Quattro significati diversi di «funzionante»

1. **Interfaccia funzionante:** navigazione, filtri, grafici, esportazione ed errori sono operativi.
2. **Calcolo funzionante:** il programma esegue davvero la previsione e le regole decisionali.
3. **Integrazione funzionante:** riceve correttamente i dati aggiornati di una specifica azienda o impianto.
4. **Prodotto affidabile in esercizio:** resta utile nel tempo, gestisce guasti, permessi, aggiornamenti, notifiche, responsabilità e costi.

I primi due livelli sono implementati e verificati per i flussi documentati. Il terzo è parziale e dipende dal prodotto. Il quarto **non è attestato** dai test locali e non va dedotto dall'aspetto professionale delle schermate.

## 2. Il filo conduttore: prepararsi a una decisione futura

I tre problemi sembrano diversi, ma hanno la stessa struttura:

- un operatore cloud deve capire se la spesa sta cambiando;
- un negoziante deve comprare prima di conoscere le vendite future;
- il proprietario di un impianto deve scegliere quando consumare prima di conoscere la produzione effettiva.

In tutti i casi esiste una storia di misurazioni e una decisione da prendere prima che il futuro sia osservabile.

L'idea non è «mettere una chat AI in tre dashboard». È usare la previsione come uno degli strumenti per prendere decisioni più informate. **La previsione descrive uno scenario; la persona decide che cosa farne.**

Una previsione accurata, da sola, non garantisce una buona decisione. Un riordino può essere statisticamente ragionevole ma economicamente troppo costoso. Un'anomalia cloud può essere una campagna prevista. Una fascia solare può essere inadatta agli orari di chi usa l'impianto.

## 3. Che cos'è una serie temporale

Una serie temporale è una sequenza di osservazioni con un ordine nel tempo: costo giornaliero, vendite giornaliere, energia oraria.

L'ordine conta. Un modello che osservasse, anche involontariamente, le vendite della settimana da prevedere avrebbe un vantaggio illegittimo. Anche l'unità conta: euro e dollari non sono intercambiabili; pezzi al giorno non sono pezzi alla settimana; energia per un impianto non è energia normalizzata per unità di potenza.

Tra le strutture che possono aiutare una previsione ci sono:

- **livello:** la grandezza tipica della serie;
- **tendenza:** una crescita o una diminuzione relativamente persistente;
- **stagionalità:** comportamenti che si ripetono, per esempio per giorno della settimana;
- **relazioni con altre variabili:** per esempio tra radiazione solare e produzione;
- **variabilità:** quanto il fenomeno oscilla anche senza un cambiamento strutturale.

Non tutto è prevedibile dai dati disponibili. Una promozione non registrata, un guasto nuovo o un cambiamento di prezzo possono modificare il futuro senza lasciare prima un segnale nello storico.

## 4. Che cos'è Timestral

Timestral è una famiglia di modelli preaddestrati di Mistral per la previsione di serie temporali. In questo progetto viene usata la libreria ufficiale e vengono caricati i pesi pubblicati da Mistral.

**Non è un chatbot generalista.** Non gli chiediamo di scrivere una spiegazione della bolletta: gli passiamo sequenze numeriche e chiediamo valori futuri e quantili previsionali. I testi, le tabelle e le regole presenti nelle applicazioni sono realizzati nel software, non generati liberamente dal modello.

### Preaddestrato non significa addestrato sulla tua azienda

Il modello arriva con parametri già appresi durante l'addestramento upstream. Qui non è stato addestrato un nuovo modello proprietario e non è stato effettuato un fine-tuning specifico sui tre domini.

L'inferenza utilizza lo storico fornito per formulare una previsione. Aggiungere osservazioni allo storico cambia il contesto disponibile, ma **non equivale a un addestramento continuo dei pesi**. Il programma non diventa automaticamente un esperto della tua azienda dopo ogni utilizzo.

### Che cosa significano 5M, 28M e 209M

Le sigle identificano taglie con circa quel numero di milioni di parametri. Un parametro è un valore interno appreso dal modello, non un prodotto del catalogo né un giorno di previsione.

Una taglia più grande può richiedere più memoria e più tempo. Non è necessariamente migliore su ogni serie, metrica o decisione. Le interfacce espongono 5M, 28M e 209M; i risultati misurati devono guidare la scelta, insieme ai vincoli hardware.

### Che cosa entra e che cosa esce

In termini semplificati:

- **input:** una sequenza storica, un orizzonte da prevedere e, nei flussi supportati, variabili aggiuntive allineate;
- **output:** una previsione centrale e quantili, cioè valori associati a differenti posizioni della distribuzione prevista.

L'adapter dei progetti espone mediana, p10, p90, p01 e p99. Le UI usano soltanto le informazioni necessarie al proprio flusso. In SolarCast B entrano anche covariate meteorologiche: storico e futuro devono essere temporalmente coerenti.

### Dove viene eseguito

L'inferenza avviene localmente su CPU nei container. Non viene inviata a un servizio remoto di generazione testuale. Il primo uso può scaricare i pesi da Hugging Face; i download dei dati pubblici e le integrazioni esplicite sono operazioni di rete separate.

«Locale» non significa certificazione di privacy o assenza di qualsiasi connessione: bisogna comunque controllare dati, cache, download, credenziali e condizioni delle fonti utilizzate.

Riferimenti: [libreria ufficiale](https://github.com/mistralai/timestral), [modello 5M](https://huggingface.co/mistralai/Timestral-5M), [licenza dei pesi](https://huggingface.co/mistralai/Timestral-5M/blob/main/LICENSE). La libreria è fissata al commit riportato in `requirements-model.txt`; ciò non blocca automaticamente tutte le dipendenze o ogni revisione dei pesi.

## 5. Perché c'è anche una modalità senza AI

Le baseline sono metodi di riferimento: ripetere un profilo recente, usare una media mobile, stimare un modello statistico o una regressione. Non sono numeri finti inseriti per riempire le schermate.

Servono a tre cose:

1. permettere un primo utilizzo leggero, senza pesi Timestral;
2. offrire un confronto comprensibile;
3. verificare se la complessità aggiuntiva del modello produce un vantaggio misurabile.

Se una regressione risolve meglio un particolare problema, il risultato corretto è mostrarlo, non nasconderlo. Il valore del prodotto non dipende dall'obbligo di far vincere l'AI.

**Aprire un'applicazione non significa aver attivato Timestral.** Controllare modello e metodo selezionati, premere Applica parametri e leggere il risultato dell'ultimo calcolo riuscito. Le preferenze salvate nel browser possono ripristinare una scelta precedente. Un errore del modello non viene sostituito di nascosto con una baseline.

## 6. L'incertezza: una banda non è una promessa

La mediana rappresenta il centro della distribuzione prevista secondo il modello. p10 e p90 delimitano una fascia centrale nominale dell'80%: non significa che l'80% dei casi reali finirà necessariamente lì.

Per affermare una copertura effettiva bisogna misurarla su osservazioni non usate per produrre la previsione e su un contesto sufficientemente rappresentativo. Un modello può essere troppo sicuro, troppo incerto o cambiare comportamento quando cambiano i dati.

Inoltre, **sommare quantili di giorni diversi non produce automaticamente il quantile del totale**. Non si può semplicemente sommare p90 giornalieri e chiamare il risultato «garanzia del 90%» per un mese o una scorta. Nei progetti queste somme sono regole euristiche, dichiarate come tali.

Le baseline puntuali non ricevono bande artificiali per sembrare equivalenti ai modelli probabilistici. L'assenza di una banda è un'informazione, non un difetto grafico da mascherare.

## 7. CloudGuard: dalla previsione al controllo dei costi

CloudGuard affronta due domande diverse: «quanto spenderò?» e «che cosa è insolito?». Prevedere bene il totale non significa necessariamente individuare bene ogni picco.

Il modello osserva costi passati per servizio. Il software prepara il calendario, gestisce valuta e provvisorietà, stima il resto del mese e confronta osservazioni con soglie. La persona interpreta la causa: un aumento può essere un errore, ma anche traffico desiderato o un'attività pianificata.

**Oggi:** la UI lavora su costi sintetici in USD. Il motore e le interazioni funzionano davvero. Il percorso AWS è disponibile separatamente in Python/CLI e richiede autorizzazione e credenziali; non è stato collaudato su un account reale. Non c'è spegnimento automatico di risorse.

**Per usarlo su un account reale:** occorrono integrazione e verifica dei dati, taratura delle soglie, gestione persistente dei giorni provvisori, deduplicazione degli invii e una procedura di risposta agli allarmi. Non è ancora un sostituto di un sistema di monitoraggio cloud in produzione.

[Approfondimento CloudGuard](cloudguard/docs/CONCEPTS.md).

## 8. StockSense: la previsione non è l'ordine

StockSense affronta un problema di anticipo: quando ordini la merce, non conosci ancora tutte le vendite che avverranno prima del prossimo rifornimento.

Il modello stima le vendite. Il software combina la previsione con giacenza, ordini in arrivo, tempi di consegna, ciclo di revisione e lotto minimo. La persona verifica sostenibilità economica, vincoli del fornitore e informazioni commerciali non presenti nei dati.

**Oggi:** sono operativi previsioni per SKU, priorità, proposte, selezione ed esportazione. Sono stati eseguiti benchmark su vendite storiche reali UCI. Nella UI, però, l'inventario è simulato: il dataset di transazioni non contiene le giacenze reali del tuo negozio. UCI deve essere presente localmente e non viene scaricato automaticamente dal browser.

**Per usarlo in un negozio reale:** bisogna collegare vendite e inventario aggiornati, riconciliare i prodotti, gestire arrivi e ordini aperti, valutare costi e stagionalità commerciale e controllare le proposte prima dell'acquisto. Nessun ordine viene trasmesso ai fornitori.

[Approfondimento StockSense](stocksense/docs/CONCEPTS.md).

## 9. SolarCast: dalla produzione prevista alla scelta degli orari

SolarCast aiuta a capire quando potrebbe essere disponibile energia fotovoltaica. Non decide al posto dell'utente quanto sia importante ogni consumo e non controlla automaticamente dispositivi.

Il modello può usare soltanto lo storico della produzione oppure anche il meteo. Il software cura unità, allineamento temporale, potenza dell'impianto e ricerca delle fasce. La persona considera fabbisogno, carichi, batteria, tariffe e produzione effettiva.

**Oggi:** la UI è retrospettiva. Usa dati sintetici o produzione PVGIS simulata da dati satellitari, con meteo storico. Non legge il tuo inverter e non mostra una previsione live del tuo impianto. L'API Python operativa esiste, ma richiede misure recenti fornite dall'utilizzatore e meteo previsto immediatamente successivo.

**Per l'uso reale:** occorrono acquisizione delle misure, controllo della freschezza, meteo previsto, gestione dei dati mancanti e verifica sull'impianto specifico. Un'eventuale automazione dei dispositivi sarebbe un'integrazione ulteriore, non già presente.

[Approfondimento SolarCast](solarcast/docs/CONCEPTS.md).

## 10. Cinque parole sui dati da non confondere

- **Sintetici:** creati da un generatore. Consentono test riproducibili e casi controllati; non provano risultati su un'azienda vera.
- **Storici reali:** osservazioni passate di un'attività reale, come le transazioni UCI. Non sono necessariamente aggiornate o rappresentative della tua attività.
- **Simulati:** prodotti da un modello o da ipotesi, come giacenza artificiale o produzione PVGIS. Non sono misure dirette del sistema che vuoi gestire.
- **Live:** aggiornati con una frequenza adeguata alla decisione. Un file recente non basta se le misure al suo interno sono vecchie.
- **Oracle:** un confronto che usa informazioni future realmente osservate, quindi non disponibili al momento in cui si sarebbe dovuto prevedere. In SolarCast riguarda il meteo futuro storico fornito a B e regressione.

Un esempio di oracle: per simulare una previsione emessa il 15 giugno si fornisce al modello il meteo effettivamente osservato il 16 giugno. Serve a studiare il modello in condizioni informative favorevoli, ma non misura l'errore che introdurrebbe una vera previsione meteorologica.

## 11. Come vengono valutati i risultati

Un backtest simula decisioni nel passato: per ogni origine si usa soltanto il prefisso disponibile e si confronta la previsione con ciò che è accaduto dopo. Questo evita di giudicare il modello solo sulla capacità di spiegare dati già visti.

Il progetto controlla anche che selezione dei servizi/SKU e trattamento degli outlier non usino indebitamente il futuro. Sono esempi di prevenzione del **data leakage**, cioè della contaminazione della valutazione con informazioni non disponibili al momento della previsione.

### Metriche diverse rispondono a domande diverse

- **MAE:** errore assoluto medio, nell'unità della variabile. Deve essere confrontato sullo stesso protocollo.
- **MASE:** errore normalizzato rispetto a una scala ricavata dallo storico; può essere indefinito su serie costanti.
- **Precisione degli allarmi:** quante segnalazioni risultano corrette.
- **Recall:** quanti casi anomali vengono trovati. Trovare almeno un giorno di un evento è diverso dal trovare tutti i giorni anomali.
- **Stockout, vendite perse e giacenza:** conseguenze di una politica di magazzino, non solo qualità della previsione.
- **Errore orario ed errore sull'energia giornaliera:** non sono intercambiabili; gli errori possono compensarsi nella somma.

I benchmark conservano anche risultati sfavorevoli a Timestral: CloudGuard 5M rileva meno giorni anomali della regola classica nel protocollo sintetico; la regressione SolarCast batte B sull'energia giornaliera nel confronto annuale; StockSense riduce gli stockout aumentando sensibilmente la merce immagazzinata. I dettagli numerici e le fonti sono nei README dei prodotti.

## 12. Che cosa dimostrano i test, e che cosa non dimostrano

Al termine della migrazione web sono passati 200 test Python, 9 flussi Chromium e tre prove HTTP con inferenza Timestral 5M reale. Sono state costruite e provate anche copie esportate dei tre repository senza dipendenze reciproche. Il registro preciso è in [VERIFICHE.md](VERIFICHE.md).

Queste prove dimostrano il funzionamento dei casi verificati, non una garanzia universale. Alcuni test usano simulazioni o errori iniettati intenzionalmente: sono adatti a verificare le regole, non sostituiscono account e sensori reali.

Non dimostrano automaticamente:

- risparmio economico per un cliente;
- qualità dei dati del tuo account, negozio o impianto;
- robustezza a qualsiasi carico o guasto;
- sicurezza per esposizione pubblica;
- conformità normativa o idoneità commerciale.

## 13. Come provarli senza fraintendere quello che vedi

1. Avviare i container seguendo il README.
2. Aprire [CloudGuard](http://localhost:8501), [StockSense](http://localhost:8502) o [SolarCast](http://localhost:8503) sul computer dove sono eseguiti.
3. Leggere sorgente, data dell'analisi e modello. Una data storica non è «oggi».
4. Provare prima la baseline; poi selezionare Timestral 5M e applicare i parametri. Il primo download può richiedere rete e tempo.
5. Confrontare risultati sullo stesso periodo. Non interpretare un numero diverso come automaticamente migliore.
6. Cambiare un parametro comprensibile e verificare che il risultato venga ricalcolato. Se il calcolo fallisce, i risultati precedenti non sono diventati nuovi risultati.
7. Esportare il CSV e leggere le assunzioni del report, non soltanto il grafico.

Non è presente un caricamento universale di file per qualsiasi attività. I percorsi di ingresso supportati sono quelli descritti nelle guide operative.

## 14. Prima di affidargli una decisione reale

Un'introduzione responsabile partirebbe da una prova in parallelo al processo esistente, senza azioni automatiche: raccogliere previsioni prodotte in tempo reale, conservarle prima dell'esito, confrontarle con ciò che accade e misurare il costo degli errori.

Bisognerebbe poi definire chi controlla i dati, chi approva un ordine, chi valuta un allarme, quando una previsione è troppo vecchia e che cosa fare se il servizio non risponde. Il beneficio deve essere misurato nel contesto reale, non importato da un benchmark diverso.

Le API attuali non hanno autenticazione o gestione multiutente: i binding Docker sono locali. Pubblicarle su Internet richiederebbe un progetto di sicurezza e gestione operativa ulteriore. Anche licenze dei pesi e condizioni dei dati/API vanno controllate prima dell'uso commerciale.

## 15. La filosofia del progetto, in una frase

**Usare modelli previsionali reali per aiutare una persona a decidere, mantenendo visibili dati, assunzioni, incertezza e limiti, anche quando il metodo più semplice ottiene un risultato migliore.**

Il traguardo non è far sembrare intelligente una schermata. È rendere controllabile il percorso che va dai dati a una proposta, senza confondere una dimostrazione verificata con un prodotto già validato sul campo.
