# Protocollo fissato prima dell'esecuzione

6 novembre 2026. Studio esplorativo nuovo per Aheadlab; i dati pubblici potrebbero
essere presenti nell'addestramento di Timestral. Non è una prova universale.

## Dati e scelta del campione

CESNET-TimeSeries24, 283 istituzioni, aggregazione oraria. Target: byte nell'ora
convertiti in Mbit/s medi (`n_bytes * 8 / 3600 / 1e6`). Non rappresenta picchi,
CPU o richieste HTTP. Fonte CC-BY-4.0, distribuzione HDF5 e checksum in
`data/source.json`. Raw esclusi da Git; riportare metadati e selezione.

Selezionare 12 istituzioni con seed 20261106, fra quelle con almeno 95% di
osservazioni valide e traffico positivo in almeno metà delle ore del training.
Ordinare gli identificativi prima dell'estrazione. Nessun filtro basato sugli
errori futuri o sull'andamento favorevole al modello.

Ultimi 56 giorni interi: 14 di calibrazione, 14 di selezione, 28 di test finale.
Tutto il prefisso precedente è training. Contesto massimo di 2016 ore (12 settimane)
identico fra i modelli. Origini giornaliere, orizzonte 24 ore, nessuna sovrapposizione.
Interpolazione bidirezionale vietata: buchi riempiti causalmente con la stessa
ora della settimana precedente, altrimenti ultimo valore noto; zero solo prima
della prima osservazione. I target mancanti non sono imputati: giorni incompleti
esclusi in modo comune a tutti i modelli; riportare numerosità effettive.

## Previsioni

Timestral 5M e 28M, snapshot fissati; ultimo valore, ieri, settimana precedente,
media delle ultime quattro settimane, ETS(A,A,A) smorzato con periodo 24,
MSTL con periodi 24/168 e trend AutoETS non stagionale, regressione ridge con
armoniche di calendario e lag 24/168. Parametri stabiliti prima del test.
Tutti utilizzano lo stesso storico riempito; nessuna variabile futura.

MAE, MASE con scala stagionale 168 calcolata sul training di ogni origine,
bias, copertura e pinball loss dei quantili ove presenti. Le metriche aggregate
non usano media geometrica con zeri. La scala MASE nulla produce null/esclusione
esplicita. Le baseline ricevono anche intervalli calibrati, per confrontare
l'incertezza senza assegnarla soltanto all'AI.

## Decisione di capacità

Un modulo offre `p95(training)/10` Mbit/s, minimo positivo; valore calcolato prima
di calibrazione/selezione/test. I moduli sono simulati e non equivalgono a SKU cloud.

Capacità richiesta `k_t = max(1, ceil((previsione_t + margine)/capacità_modulo))`.
Margine = massimo fra zero e il quantile degli errori orari `reale - previsto`
sui 14 giorni di calibrazione. Stesso metodo per tutti, quantili candidati
0 / 0,5 / 0,75 / 0,9 / 0,95 / 0,975 / 0,99 / 1. Scorta non basata sui quantili
marginali del solo modello AI. Margine congelato prima della selezione.

Ritardo di attivazione un'ora: la prima ora di ogni piano mantiene la capacità
precedente; le successive possono applicare il piano giornaliero. Nessun backlog
nel simulatore: misura deficit di capacità oraria, non latenza/packet loss/SLA.

Per ogni modello scegliere un quantile globale sul periodo di selezione:
minime unità-ora fra quelli con deficit <= 1% del traffico normalizzato per
capacità del modulo. Se nessuno soddisfa il vincolo, scegliere il minor deficit
e dichiarare non fattibilità. Scegliere anche una baseline e una taglia AI con
questa regola, prima di esaminare il test. Conservare tutti i risultati.

Il test usa le scelte congelate. La normalizzazione permette di confrontare
istituzioni di scala diversa; non è capitale monetario e non è somma di euro.
Una seconda misura di deficit in traffico grezzo può essere descrittiva.

## Criterio primario e incertezza

Confronto della taglia AI e della baseline scelte sulla selezione. Successo se:

1. Entrambe sono fattibili sul periodo di selezione e sul test (deficit <= 1%).
2. Risparmio puntuale di unità-ora AI almeno 10% e limite inferiore dell'intervallo
   bootstrap al 95% maggiore di zero.
3. Limite superiore dell'intervallo della differenza di deficit AI − baseline
   non oltre 0,2 punti percentuali (margine di non inferiorità predefinito).

2000 ricampionamenti, seed 20261106; istituzioni e blocchi circolari di sette
giorni ricampionati mantenendo accoppiate le previsioni. Riportare l'incertezza
condizionata a questo campione. Risultati degli altri modelli secondari e
descrittivi; non sostituire il vincitore dopo aver visto il test.

Un esito negativo rimane nel report e nella dashboard. «Prova matematica» qui
significa formule esplicite, controlli di conservazione e evidenza statistica
empirica; non un teorema che garantisca vantaggi su dati futuri.

## Risorse

Un job alla volta: 2 GiB RAM, 1 CPU, zero swap aggiuntivo, nessuna rete per
inferenza. Download dati esplicito e separato, streaming e checksum. Nessun
arresto dei container esistenti. Codice e demo dei tre progetti precedenti intatti.
