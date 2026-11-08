# Seconda ricerca: dalla diagnosi alla verifica su dati nuovi

7 novembre 2026. La prima ricerca rimane invariata e consultabile.

1. Ricostruire i piani dai risultati già salvati; verificare che i totali
   coincidano con il primo report. Separare deficit per istituzione, giorno,
   ora, picchi e prima ora del piano. Quantificare quanto dipende da pochi
   eventi e quanto dal margine fisso o dal ritardo di attivazione.
2. Definire una correzione motivata dai risultati della diagnosi, con le stesse
   possibilità per modelli AI e classici. Scrivere un protocollo prima di
   misurare i risultati del nuovo periodo finale.
3. Procurare dati successivi al primo test. CESNET-TimeSeries26 è un candidato
   degli stessi autori che estende la raccolta fino al 2026; verificarne
   provenienza, dimensioni, schema, controlli di qualità e periodo effettivo.
4. Implementare simulazione causale, test di assenza di accesso al futuro e
   confronto con politica originale e baseline reattiva. Selezionare i
   parametri prima del test; conservare anche risultati sfavorevoli.
5. Eseguire un test temporale nuovo, stimare incertezza a blocchi, verificare
   concentrazione del deficit e utilità marginale dell'AI. Non chiamare
   risparmio monetario ciò che misura capacità simulata.
6. Aggiornare ricerca e testo portfolio con spiegazione semplice, prove,
   limiti, esito e indicazione precisa di cosa resta da verificare in produzione.

Risorse: RAM host disponibile iniziale 9,30 GiB. Container temporanei con
2 GiB RAM e una CPU, nessuna rete per il calcolo, controllo della riserva host.
Download separato e in streaming. Dashboard spenta; servizi preesistenti
intatti. Nessun processo modello deve restare attivo a fine lavoro.

## Completamento, 8 novembre 2026

Completati i sei punti: diagnosi ricostruita, protocollo congelato, dataset
CESNET-TimeSeries26 verificato, politiche implementate, 28 test Python passati,
18.144 previsioni e confronto di 241 configurazioni. Test finale: 24 istituzioni
per otto settimane. Analisi dei componenti, incertezza statistica e misure
di tempo/RAM concluse; [ricerca](RESEARCH_V2.md) e
[testo portfolio](../../PORTFOLIO_RICERCA.md) aggiornati.

Esito: errore 28M inferiore del 35,80% a ETS, ma piano con capacità +1,20%
e deficit 1,540% contro 1,496%. Correzione verificata, criterio operativo
non raggiunto. Nessuna modifica delle scelte primarie dopo il test.

Minimo RAM host campionato 8,39 GiB; otto servizi preesistenti invariati.
Dashboard spenta e container temporanei terminati. Questa ricerca è conclusa;
una validazione in produzione richiederebbe dati e vincoli del servizio reale
e costituisce un esperimento diverso, non un risultato qui rivendicato.
