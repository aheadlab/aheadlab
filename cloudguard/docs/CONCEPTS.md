# Capire CloudGuard: prevedere la spesa non significa conoscere la causa

Questa guida spiega il prodotto senza richiedere conoscenze tecniche. È autonoma: può essere letta anche quando CloudGuard viene esportato in un repository separato. Per avvio e comandi: [README](../README.md), [guida operativa](OPERATIONS.md), [API HTTP](API.md).

## Il problema che affronta

La spesa cloud è il risultato di molte attività: traffico, risorse attive, database, storage e processi automatici. Aspettare la fattura può rendere costoso accorgersi di un cambiamento.

CloudGuard aiuta a rispondere a due domande:

1. Quanto potrebbe costare il mese se il comportamento futuro fosse compatibile con i dati disponibili?
2. Quali costi osservati sono abbastanza insoliti da meritare un controllo?

Non risponde automaticamente a una terza domanda: «qual è la causa certa dell'aumento?». Un picco può essere una risorsa dimenticata, ma anche una campagna commerciale riuscita. Il software non conosce il contesto organizzativo se non gli viene fornito.

## Il ruolo di Timestral

Timestral è un modello preaddestrato di Mistral per serie temporali: riceve numeri ordinati nel tempo e stima quelli futuri. Non è un chatbot e non produce una diagnosi testuale libera dell'account.

Qui viene eseguito il modello ufficiale, senza un nuovo addestramento specifico per CloudGuard. Le taglie 5M, 28M e 209M indicano approssimativamente milioni di parametri, non giorni di previsione. Una taglia maggiore non garantisce risultati migliori.

L'inferenza avviene su CPU locale. Il primo utilizzo può scaricare i pesi da Hugging Face; ciò è distinto da una chiamata AWS. Il progetto include anche baseline statistiche: al primo accesso il workspace parte da una baseline, non da Timestral. Le preferenze successive persistono nel browser.

## Che cosa fa il modello e che cosa fa il software

Il modello fornisce una previsione della serie di un servizio e i suoi quantili. Il software:

- prepara il calendario giornaliero e conserva la valuta;
- distingue importi finalizzati e provvisori nei percorsi AWS;
- somma la spesa osservata e la previsione del periodo residuo per stimare il mese;
- applica regole per decidere se segnalare un'osservazione;
- mostra risultati, confronti e metadati.

La baseline mensile ripete una struttura settimanale recente. La regola classica per le anomalie usa media, variabilità recente e scarto minimo. Una baseline è un metodo reale di calcolo, non un risultato dimostrativo scritto a mano.

## Un esempio ragionato

Esempio puramente illustrativo, **non un risultato del benchmark**: al ventesimo giorno del mese sono stati spesi 200 USD e il calcolo stima altri 100 USD. La stima mensile è 300 USD. Non è una fattura futura già nota.

Se il costo giornaliero tipico è 10 USD e un giorno vale 80 USD, il software può segnalarlo. Questo non dimostra né un guasto né una frode. La persona dovrebbe verificare quali risorse e attività spiegano la differenza.

Analogamente, una mancata segnalazione non dimostra che tutto sia corretto: soglie, storico e ritardi possono impedire di individuare un problema.

## Come leggere l'interfaccia

- **Panoramica:** spesa osservata nel mese, stima finale, previsione per l'orizzonte scelto e segnalazioni.
- **Costi per servizio:** distribuzione degli ultimi 30 giorni; selezionare un servizio apre la sua previsione.
- **Centro anomalie:** registro retrospettivo, filtri e dettaglio osservato/atteso/soglia. Un giorno può avere record distinti per metodo.
- **Analisi e benchmark:** report già calcolati, tabelle, ricerca ed esportazione.

Il cutoff consente di fermare lo storico prima della sua fine e analizzare un mese ancora in corso. La data esposta è quella dei dati, non necessariamente quella del computer. Premere Applica parametri per ricalcolare: cambiare un controllo non aggiorna retroattivamente il vecchio risultato.

## Perché le bande non sono garanzie

p10 e p90 descrivono quantili del modello. La loro somma sul mese è un'indicazione euristica, non un intervallo calibrato del totale. La dipendenza tra giorni conta e non viene risolta sommando estremi.

La baseline non ha una distribuzione probabilistica equivalente: il software non inventa una banda per renderne il grafico più convincente.

## Stato reale del prodotto

**Funziona oggi:** interfaccia React, API FastAPI, previsioni reali, stime mensili, analisi delle anomalie, report, CSV e inferenza Timestral selezionabile. Il motore non viene sostituito silenziosamente se fallisce.

**Dati della UI:** sintetici in USD, riproducibili. Non sono la bolletta dell'utilizzatore. Il browser non accede ad AWS e non invia Telegram.

**Integrazione disponibile separatamente:** ingest AWS e invio esplicito attraverso Python/CLI. Non sono stati collaudati con credenziali reali. Le prove con client simulati verificano il codice, non l'intero rapporto con un account AWS.

**Non presente:** monitoraggio operativo completo con recupero persistente dei giorni saltati perché provvisori e deduplicazione degli invii. Non vengono spente risorse automaticamente e non viene garantito un risparmio.

## Cosa insegnano i risultati misurati

Nel benchmark sintetico completo, Timestral 5M migliora l'errore della previsione a 30 giorni rispetto alla baseline settimanale. Ma rileva 11 dei 22 giorni anomali valutati, contro 21 della regola classica. Entrambi rilevano almeno un giorno per ciascuno dei 10 eventi valutabili.

Non c'è contraddizione: prevedere bene e individuare tutti i giorni di un'anomalia sono obiettivi diversi. Il risultato non va trasformato in «AI sempre migliore» né in prova di efficacia su AWS reale. Numeri e protocollo completi sono nel README.

## Che cosa manca per usarlo su un account reale

Occorre verificare permessi e costi di Cost Explorer, completezza dello storico, valuta, gestione dei dati provvisori e significato di eventuali crediti. Servono soglie adatte all'account, uno stato persistente e una procedura umana per classificare gli allarmi.

Una prova responsabile raccoglierebbe prima segnalazioni senza azioni automatiche, misurando falsi allarmi e problemi non rilevati. I 65 test Python e i tre flussi browser verificati documentano il software, non sostituiscono questa prova sul campo.

Le API attuali sono locali e senza autenticazione. Per un servizio pubblico servirebbero ulteriori controlli di sicurezza, gestione utenti e operatività. Prima dell'uso commerciale verificare anche la [licenza Timestral](https://huggingface.co/mistralai/Timestral-5M/blob/main/LICENSE).

**In sintesi:** CloudGuard è un'applicazione di analisi funzionante su un contesto dimostrativo controllato, con componenti di integrazione disponibili. Non è ancora un monitoraggio validato del tuo account AWS.
