# CarbonShift: protocollo del confronto operativo

9 novembre 2026. Scritto dopo l'esplorazione gennaio–giugno 2025 e prima
di calcolare il risultato operativo sui periodi di conferma. Non è una
preregistrazione esterna. Il benchmark previsionale degli autori è già pubblico;
la nostra domanda nuova riguarda le decisioni di programmazione.

## Caso concreto e criterio

Un'attività elettrica differibile dura quattro ore consecutive e deve essere
conclusa entro le prossime 96 ore. Esempi: elaborazione batch, rendering,
ricarica senza esigenza immediata. La potenza è costante, il consumo totale è
uguale per ogni metodo. Nessuna attività viene cancellata o spostata oltre
scadenza; non si cambia zona geografica. Ogni caso rappresenta un lavoro
isolato: non si simula una coda di lavori concorrenti.

La decisione è l'ora di avvio, scelta minimizzando la media dell'intensità
carbonica prevista sulle quattro ore. A parità vince l'avvio più vicino.
Il risultato usa l'intensità verificatasi nelle ore scelte, non il MAE.
Emissioni attribuite (kg) = kWh del lavoro × intensità media (g/kWh) / 1000.
Si tratta di un indicatore contabile basato sul mix di produzione, non di
emissioni marginali causalmente evitate o di CO2 misurata sul lavoro reale.

Successo operativo nel campione: emissioni attribuite almeno **0,5% inferiori**
alla migliore baseline selezionata sullo sviluppo, intervallo al 95% della
riduzione interamente positivo, tutti i lavori completati e stesso consumo.
Riportare anche la differenza assoluta in g/kWh e kg per MWh: un miglioramento
percentuale piccolo non diventa una promessa di ROI. La soglia dello 0,5%
è fissata qui come effetto minimo del caso portfolio, non come convenienza
economica già dimostrata. Riportare energia di inferenza non misurata.

## Fonte e separazione temporale

Dati e previsioni Khepri-TSFM v1.0.1, commit
`f968f271487a110956ff1e29b9a88001d523aeb4`,
https://github.com/avalyset/khepri-tsfm,
https://doi.org/10.5281/zenodo.23912503,
https://arxiv.org/abs/2611.02895.
File verificati con identificatori blob Git e SHA-256 locale. Licenza dati
CC-BY-4.0; attribuzione a Eirik Botten Nicolaysen / EcoDeco AS.

- Sviluppo: origini 1 gennaio–30 giugno 2025, già esplorate per questa scelta.
- Periodo separato: origini 5 luglio–27 dicembre 2025; quattro giorni di
  separazione evitano sovrapposizione dei target con lo sviluppo.
- Controllo dopo il rilascio del modello: 16–29 ottobre 2026, solo 14 origini,
  riportato separatamente con incertezza; non sostituisce il periodo lungo.
- Primario: sei zone senza ore di target riempite nella documentazione
  della fonte, NO1, NO4, SE1, SE2, SE3, SE4. NO2, NO3 e NO5 hanno problemi
  documentati di valori imputati: escluse per qualità, non per graduatoria.
  Tabella secondaria su tutte le nove zone.
- Il controllo di schema ha mostrato le prime due righe del 16 ottobre 2026,
  per riconoscere le colonne, prima del protocollo. Nessuna scelta di finestra
  o risultato operativo di quel periodo è stata esaminata.

Tutte le ore devono essere finite, non negative, senza duplicati; h=1..96 e
target_time=origin+h. I valori effettivi devono coincidere fra file dei metodi
e serie della fonte. Non sostituire casi sfavorevoli.
La fonte usa osservazioni fino all'ora di origine inclusa: il caso assume
disponibile quella misura e programma dalle ore successive. Tempi di
pubblicazione/revisione ENTSO-E non sono simulati; non è una prova live.

## Modelli e scelta

Timestral 5M con snapshot `bdd20cfc15a3fea0e4cb5ccef37f8d3ca7aa335f`,
contesto 8192 ore, orizzonte 96, senza covariate. Primario: mediana pubblicata,
coerente con la fonte. L'approssimazione della media dai quantili è stata
esplorata, ma non viene sostituita dopo il test.

Baseline: SARIMA e GBM pubblicati dagli autori, settimana precedente,
giorno precedente ripetuto, profilo orario medio degli ultimi 28 giorni,
avvio immediato. Aggiungere un orario fisso per zona, scelto sui dati 2024
come il blocco di quattro ore con intensità media più bassa; resta fisso.
Selezionare la baseline primaria sullo sviluppo usando le sei zone primarie;
scrivere la scelta prima di calcolare il test. Nessuna promozione del
migliore sul test. Riportare comunque tutte le alternative.

Un vantaggio contro queste baseline non dimostra superiorità contro ogni
modello moderno o un GBM riaddestrato con un diverso protocollo. Il benchmark
eredita addestramenti e limitazioni della fonte, esplicitati nel report.
Ricalcolare localmente un campione sistematico di previsioni 5M e confrontarlo
con l'archivio, senza chiamare tutti i file pubblicati inferenze fatte da noi.

## Statistica e controlli

5000 bootstrap accoppiati a blocchi circolari di 7 giorni, seed 20261109.
Le sei zone sono mantenute insieme: l'inferenza riguarda queste zone fisse
e tiene conto dei loro shock comuni, non la popolazione di reti mondiale.
Riportare sensibilità con blocchi 14 giorni, risultati per zona, quota di
giorni migliori, differenza rispetto ad avvio immediato e regret rispetto
all'oracolo che conosce il futuro (solo limite ideale, non concorrente).

Le finestre di 96 ore si sovrappongono: non contare le ore come osservazioni
indipendenti. Nel controllo di 14 origini l'incertezza resta elevata.
I dati 2025 possono essere stati visti in pretraining. Il controllo 2026
riduce questo problema per i target, senza essere una prova prospettica.

Test software: invarianti di energia/durata/scadenza, selezione senza target,
indipendenza dalle osservazioni future, gestione input, unità kg/g/kWh,
confronto statistico identico a zero. Dashboard come replay verificabile.

## Risorse e isolamento

Container temporanei: 2 GiB, una CPU, rete disabilitata, nessuno swap extra.
Avvio con almeno 5 GiB host liberi, arresto del solo job sotto 4 GiB. Otto
servizi preesistenti invariati. I quattro progetti precedenti non cambiano.
Download di dati pubblici separato dal calcolo; nessun nuovo peso scaricato.
