# Capire SolarCast: prevedere l'energia senza confondere passato e futuro

Questa guida spiega il prodotto a chi non conosce modelli AI o pipeline dati. È autonoma e può accompagnare il repository esportato. Per uso e comandi: [README](../README.md), [guida operativa](OPERATIONS.md), [API HTTP](API.md).

## Il problema che affronta

Un impianto fotovoltaico non produce la stessa energia in ogni ora. Sapere quando potrebbe produrne di più può aiutare a spostare consumi compatibili con le proprie esigenze.

SolarCast formula una previsione a 48 ore e individua fasce che superano una soglia per una durata minima. Aiuta a valutare «quando potrebbe essere conveniente consumare», ma non conosce automaticamente tutti i carichi, le tariffe, la batteria o le priorità della casa.

**Energia prodotta non equivale a energia in surplus.** Se altre utenze stanno già consumando, una fascia di produzione elevata potrebbe non lasciare energia disponibile per un carico aggiuntivo. L'applicazione non calcola un bilancio completo della casa né un risparmio in bolletta garantito.

## Il ruolo del modello AI

Timestral è un modello preaddestrato di Mistral per serie temporali. Riceve sequenze di numeri e produce previsioni e quantili. Non è un chatbot, non consulta autonomamente il tuo impianto e non genera spiegazioni meteorologiche libere.

Il progetto usa il modello ufficiale senza addestrare un nuovo modello SolarCast. Le taglie 5M, 28M e 209M indicano milioni di parametri approssimativi; una taglia più grande può costare più tempo e memoria senza essere sempre migliore.

L'inferenza avviene localmente su CPU. Il primo download dei pesi è un'operazione di rete distinta dal download dei dati meteo.

### Quattro metodi, non una sola risposta obbligatoria

- **Persistenza 24 ore:** ripete il profilo recente. È un riferimento semplice, non AI Timestral.
- **Regressione sulla radiazione:** stima una relazione tra radiazione e produzione sullo storico recente.
- **Timestral A:** usa lo storico della produzione.
- **Timestral B:** usa anche radiazione, nuvolosità e temperatura, allineate tra passato e futuro.

Il primo accesso usa la persistenza. Per usare Timestral bisogna selezionare modello e metodo appropriati e applicare i parametri; le preferenze successive possono essere ripristinate dal browser.

## Le unità fanno parte della correttezza

- **kWp:** potenza nominale dell'impianto in condizioni di riferimento.
- **kW:** potenza, cioè ritmo di produzione o consumo.
- **kWh:** energia accumulata durante un intervallo.
- **kWh/kWp:** energia normalizzata per unità di potenza nominale.

Internamente la produzione è normalizzata per 1 kWp. Per visualizzare la produzione dell'impianto si applica la potenza nominale una sola volta. La risposta HTTP contiene già valori scalati: il frontend non deve moltiplicarli di nuovo.

Esempio illustrativo, **non dato misurato**: 0,5 kWh/kWp in un'ora, per 6 kWp, corrispondono a 3 kWh in quell'ora. Non corrispondono a una misura costante di 3 kW in ogni istante: la variazione interna all'ora non è descritta da quel singolo campione.

## Tre contesti profondamente diversi

### Demo sintetica

Un generatore crea produzione e meteo artificiali per provare la pipeline senza servizi esterni. I calcoli sono reali, ma i dati non rappresentano il tuo tetto. Coordinate e geometria non modificano quel generatore come farebbero in una simulazione fisica localizzata.

### Analisi storica PVGIS

PVGIS fornisce una stima della produzione basata su dati satellitari e parametri dell'impianto. **È produzione simulata, non una lettura del tuo contatore.** SolarCast la combina con meteo storico per confrontare i metodi nel passato.

Il browser richiede consenso prima di scaricare questi dati pubblici. La disponibilità dei servizi e dell'anno richiesto può cambiare; un errore non attiva silenziosamente una sorgente diversa.

### Previsione operativa

Richiederebbe produzione recente realmente misurata e meteo previsto per le ore immediatamente successive. La funzione Python con `operational=True` esiste e verifica la freschezza temporale, ma non acquisisce da sola le misure dal tuo inverter.

La UI attuale serve i primi due contesti, **non una previsione live già configurata**. Non è corretto prendere PVGIS di anni fa, aggiungere il meteo di oggi e presentare il risultato come la previsione di domani.

## Che cosa significa «meteo oracle»

In un confronto retrospettivo è possibile conoscere il meteo che si è effettivamente verificato nel periodo da prevedere. Se lo si fornisce a Timestral B o alla regressione, il metodo riceve informazioni che in esercizio non sarebbero ancora note.

Questo viene chiamato confronto oracle: informativamente ottimistico, utile a studiare il modello, ma non misura il peggioramento introdotto dagli errori di una vera previsione meteo. Non è un limite superiore matematico garantito per ogni metrica o caso.

Timestral A e persistenza non usano le covariate meteorologiche future per produrre la previsione. La presenza del meteo nel grafico non significa da sola che ogni metodo lo utilizzi.

## Come vengono trovate le fasce

Il software cerca blocchi contigui in cui la previsione supera una soglia per il numero minimo di ore richiesto. Con quantili disponibili usa p10 come criterio; senza p10 usa la mediana e dichiara le fasce indicative.

L'energia attesa della fascia deriva dalla mediana. La fine dell'intervallo è esclusiva: una fascia 10:00–12:00 comprende le ore che iniziano alle 10 e alle 11, non quella che inizia alle 12. Il calcolo della durata tiene conto del tempo effettivamente trascorso, anche nei cambi d'ora.

Non vengono inviati comandi a lavatrici, batterie o inverter. Una fascia non è una prenotazione di energia. Nessuna fascia disponibile può essere un risultato corretto: la soglia non viene superata abbastanza a lungo.

Anche p10 resta una previsione: non garantisce energia disponibile per tutta la fascia. Sommare quantili orari non genera un intervallo calibrato del totale giornaliero.

## Come leggere il workspace

- **Panoramica impianto:** energia nelle 48 ore, massimo orario, numero e durata delle fasce.
- **Previsione 48 ore:** grafico, dettaglio orario, radiazione e target storico disponibile per confronto.
- **Agenda consumi:** elenco e filtro delle fasce con esportazione CSV.
- **Analisi e benchmark:** report e metadati dei protocolli eseguiti.

Le ore sono visualizzate in Europe/Rome; i totali giornalieri sono aggregati su giorni UTC. Per questo il confine visivo del giorno locale può non coincidere con quello delle somme giornaliere.

Origine, potenza, fonte e metodo devono essere letti insieme. Una previsione con origine nel 2023 non diventa attuale perché oggi si apre la pagina.

## Che cosa è realmente verificato

Funzionano backend, metodi previsionali, singola applicazione della potenza, ricerca delle fasce, grafici, dettagli ed esportazioni. Durante la migrazione sono passati 60 test Python e tre flussi browser, oltre alla prova HTTP con Timestral 5M/B reale.

È stato eseguito un benchmark annuale PVGIS 5M con 364 origini nel 2023. In quel protocollo la regressione ha un errore minore di B sull'energia giornaliera, mentre B ha un errore orario diurno inferiore. Non è una contraddizione: sono obiettivi diversi. Il confronto usa meteo futuro osservato; non prova risparmi su un impianto attuale. Il report 28M è uno smoke stagionale separato, non un confronto annuale equivalente.

## Che cosa manca prima dell'uso quotidiano su un impianto

Servono almeno misure aggiornate dell'impianto, normalizzazione corretta, allineamento UTC, meteo previsto realmente disponibile e controlli sui dati mancanti. Neve, ombre locali, sporco e guasti possono alterare la produzione e non vengono risolti automaticamente dalla maggiore dimensione del modello.

Una prova utile registrerebbe previsioni emesse prima dell'esito e le confronterebbe con la produzione successiva. Per consigliare autoconsumo effettivo servirebbe anche conoscere i consumi e, se presente, lo stato della batteria.

Le API locali non hanno autenticazione. Inverter, notifiche reali e automazione dei dispositivi non sono integrati e validati come sistema operativo. Condizioni d'uso e attribuzioni PVGIS/Open-Meteo e licenza dei pesi restano da rispettare.

**In sintesi:** SolarCast è un'applicazione funzionante di previsione e analisi retrospettiva, con una funzione Python per scenari operativi forniti dall'utilizzatore. Non è ancora un servizio live collegato al tuo impianto.
