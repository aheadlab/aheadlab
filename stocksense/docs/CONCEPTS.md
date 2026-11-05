# Capire StockSense: dalla domanda prevista a una proposta di acquisto

Questa introduzione è leggibile senza conoscenze di AI ed è autonoma rispetto al portfolio. Per comandi e configurazione: [README](../README.md), [guida operativa](OPERATIONS.md), [API HTTP](API.md).

## Il problema: ordinare prima di conoscere le vendite

Un negozio deve decidere quanto comprare mentre una parte della domanda futura è ancora sconosciuta. Comprare troppo poco può causare vendite perse; comprare troppo può immobilizzare capitale, occupare spazio o generare invenduto.

StockSense non cerca semplicemente «il numero più preciso». Cerca di rendere esplicito il passaggio dalla previsione a una proposta di riordino, così che una persona possa controllarne le ipotesi.

Uno **SKU** è l'identificatore di un prodotto o variante. Le vendite vengono organizzate in serie giornaliere per SKU, mantenendo anche i giorni a zero. Quegli zeri richiedono interpretazione: potrebbero indicare assenza di domanda, ma anche indisponibilità del prodotto.

## Che cosa fa Timestral

Timestral è un modello preaddestrato di Mistral per serie temporali. Riceve uno storico numerico e stima valori futuri e quantili. Non è un assistente testuale e non conosce autonomamente fornitori, margini, promozioni o inventario.

Il progetto usa il modello ufficiale senza addestrare da zero un modello StockSense. L'inferenza viene eseguita localmente su CPU; i pesi possono essere scaricati al primo uso. Le taglie 5M, 28M e 209M indicano milioni di parametri approssimativi, con costi computazionali diversi e senza una garanzia universale di superiorità.

Sono disponibili anche media mobile, seasonal naive e AutoETS. Si tratta di modelli di riferimento realmente calcolati, non di dati di riempimento. Il workspace parte con media mobile al primo accesso; le scelte successive persistono nel browser.

## La previsione è soltanto una parte della decisione

Il modello stima le vendite. Per arrivare alla proposta servono anche:

- **giacenza:** merce disponibile;
- **in arrivo:** ordini già emessi e non ancora ricevuti;
- **lead time:** giorni necessari al rifornimento;
- **ciclo:** intervallo tra revisioni dell'ordine;
- **lotto minimo:** quantità minima acquistabile secondo la configurazione.

La regola considera il fabbisogno nel periodo lead time più ciclo e lo confronta con la disponibilità, che include la merce in arrivo. Le quantità proposte sono arrotondate e rispettano il minimo. Qui il lotto è un minimo, **non un multiplo**.

Queste sono regole del software. Non sono decisioni discrezionali prese da un agente AI e non includono automaticamente tutti i vincoli economici di un'azienda.

## Un esempio concreto, ma illustrativo

I numeri seguenti servono a spiegare il meccanismo, **non sono risultati del benchmark**.

Supponiamo che la domanda stimata nella finestra rilevante sia 100 pezzi, con 30 disponibili e 20 già in arrivo. In una politica puntuale senza margine aggiuntivo, il fabbisogno residuo è 50 pezzi, prima di applicare eventuali vincoli del lotto.

Se il fornitore è in ritardo, i 20 pezzi non arriveranno quando ci si aspetta. Se è prevista una promozione non rappresentata nei dati, la domanda potrebbe essere diversa. Se il budget non consente l'acquisto, la proposta non è attuabile. Una previsione corretta non elimina queste verifiche.

Il CSV è una proposta da controllare, non un ordine già spedito al fornitore.

## Scorta di sicurezza e incertezza

Timestral espone una previsione centrale e quantili. Il progetto può usare somme di quantili giornalieri per aumentare la scorta rispetto alla previsione centrale.

Questa è una regola euristica: scegliere p90 **non garantisce un servizio del 90%** sulla domanda aggregata. La somma di p90 di giorni diversi non è automaticamente il p90 della loro somma.

Le baseline puntuali non hanno una scorta quantile inventata. Per questo il confronto tra una politica Timestral p90 e una baseline puntuale non è un confronto tra politiche con identica protezione dal rischio: una può semplicemente tenere molta più merce.

## Come leggere il workspace

- **Panoramica:** prodotti analizzati, priorità urgenti, quantità proposte e giacenza simulata.
- **Piano di riordino:** ricerca, filtro priorità, ordinamento, paginazione, selezione multipla ed esportazione delle righe con quantità positiva.
- **Catalogo e previsioni:** storico, previsione e proiezione della giacenza senza nuovi arrivi. Non è una simulazione completa di tutti gli ordini futuri.
- **Analisi e simulazioni:** risultati dei benchmark registrati e rispettivi metadati.

La data decisionale segue la fine dello storico, non necessariamente il giorno corrente. Gli override globali devono essere attivati esplicitamente; altrimenti vale la configurazione per SKU in `config/prodotti.csv`.

In caso di errore del ricalcolo, possono restare visibili i risultati precedenti: non diventano validi per i parametri nuovi solo perché sono ancora sullo schermo.

## Dati reali e inventario simulato non sono la stessa cosa

La sorgente predefinita usa transazioni artificiali. È disponibile anche Online Retail II, un dataset UCI di transazioni commerciali storiche reali, con licenza e attribuzione documentate nel README.

La realtà delle transazioni **non rende reale la giacenza**: il dataset non fornisce l'inventario aggiornato del tuo negozio. Le risposte web usano giacenze simulate e riproducibili. Anche i benchmark di magazzino simulano ordini, arrivi e consumi.

UCI è inoltre storico, non un flusso live. Il file Excel deve essere già disponibile al backend; il browser non lo scarica automaticamente. Nel container va montato esplicitamente, come spiegato nella guida operativa. La sostituzione del file invalida la cache tramite la sua impronta.

Non è presente un connettore Shopify già operativo né un caricamento universale di qualsiasi esportazione gestionale.

## Stato reale: cosa funziona e cosa manca

**Funziona:** pipeline di pulizia, previsioni per SKU, regole di riordino, configurazione, simulazione, backend, grafici, filtri, dettagli e CSV. Sono stati eseguiti anche benchmark completi su UCI con Timestral 5M, 28M e 209M.

**Non è ancora collegato:** il tuo catalogo corrente, le tue vendite, le giacenze fisiche, gli ordini aperti e gli effettivi tempi dei fornitori.

**Non fa:** acquisti automatici, ottimizzazione economica completa, gestione multiutente o promessa di eliminare gli stockout.

Sono passati 75 test Python e tre flussi browser nella verifica della migrazione. Sono prove del funzionamento dei casi testati, non una validazione commerciale su un negozio specifico.

## Che cosa insegnano i benchmark

Nei confronti UCI pubblicati, Timestral ha un errore medio di previsione inferiore alle baseline confrontate e le politiche simulate producono meno stockout. Ma mantengono anche una giacenza media molto più alta.

Questo è un compromesso, non un risparmio dimostrato. Per sapere quale politica convenga servono almeno costi del capitale, spazio, margini, deperibilità e costo delle vendite perse.

Alcuni aggregati MASE geometrici sono zero perché esistono casi singoli con errore zero. Non significa che tutte le previsioni siano perfette. Per interpretare il confronto bisogna leggere MAE, distribuzioni per SKU e protocollo insieme.

## Un percorso responsabile verso un uso reale

Prima occorre mappare i codici prodotto e riconciliare vendite, resi, giacenze e arrivi. Poi produrre proposte senza inviarle, confrontarle con le decisioni dell'operatore e registrare esiti e costi. Promozioni, rotture di stock, festività e prodotti nuovi richiedono particolare attenzione.

Solo dopo una prova sul campo si potrebbe progettare un'integrazione con il gestionale e una procedura di approvazione. Le API attuali sono locali, senza autenticazione, e non vanno esposte pubblicamente come se fossero un servizio multiutente.

**In sintesi:** StockSense è un motore di analisi e proposta riordini funzionante, verificato anche su vendite storiche reali. Non è ancora il sistema operativo del tuo magazzino.
