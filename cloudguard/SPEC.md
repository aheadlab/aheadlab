---
id: cloudguard-contract
type: module-design
status: draft
title: CloudGuard — costi e allarmi
---

# CloudGuard — costi e allarmi

Lo stato AWS è conservato anche per giorni senza Groups tramite metadati giornalieri; altrimenti il completamento del calendario trasformerebbe un costo provvisorio in uno zero definitivo. La selezione dei servizi nel benchmark è congelata prima della prima origine; daily filtra i dati al cutoff prima del pivot e determina l'idoneità sul solo training. Il monitoraggio daily non ha catch-up persistente: un giorno saltato perché provvisorio non viene automaticamente recuperato quando definitivo, e gli invii espliciti ripetuti non sono deduplicati. Non è un monitoraggio di produzione senza stato persistente.

Pipeline autonoma da dati giornalieri per servizio a previsione, stima di fine mese e allarmi. La demo usa dati sintetici a seed fisso, senza accesso AWS o Telegram. L'ingest AWS pagina Cost Explorer, conserva valuta e stato Estimated; gli allarmi escludono giorni provvisori e attendono almeno due giorni. Valute diverse non possono essere aggregate.

Timestral è confinato in forecaster.py, restituisce vettori 1D anche a orizzonte uno e non viene sostituito tacitamente. Il confronto rolling usa stagionale settimanale, media 28 giorni e regola 3 sigma. Precisione/recall giornalieri e rilevazione degli eventi sintetici sono distinguibili, con denominatore limitato agli eventi nel periodo valutato.

Le somme di quantili giornalieri per il mese non sono quantili del totale: la banda è un'indicazione euristica senza garanzia di copertura. Il calendario mensile si riferisce all'ultimo dato disponibile. Invio Telegram è esplicito, con timeout e gestione errore HTTP; la schedulazione predefinita non invia messaggi reali.

## Contratti implementativi
Dati lunghi: `data` (giorno senza timezone), `servizio`, `costo` finito, `valuta`, `estimated` booleano. Crediti negativi sono conservati. Il pivot completa i giorni mancanti con zero (ipotesi esplicita di assenza di costi); conserva le date Estimated negli attributi. Per prudenza, un allarme non è valutato se il suo prefisso contiene qualsiasi data Estimated: non si comprimono i giorni né si sostituiscono i provvisori con zeri. Il job sceglie come ultimo giorno candidato quello disponibile non successivo a oggi meno due giorni.

Demo: 400 giorni terminanti il 2025-12-31, seed 7, USD, cinque servizi e tre eventi per servizio, etichette giornaliere ed eventi separati. Il calendario mensile usa il cutoff selezionato, incluso febbraio bisestile. La baseline mensile è seasonal naive senza banda; gli allarmi baseline usano media 28 giorni più tre deviazioni standard della popolazione e scarto minimo 5 unità della valuta originale.

Benchmark completo: due orizzonti 7/30, 20 origini per servizio distanti 7 giorni; anomalie su ciascuno degli ultimi 300 giorni con almeno 28 osservazioni precedenti. Eventi parzialmente sovrapposti alla finestra contano una volta, solo se almeno un loro giorno è effettivamente valutato per quel servizio. Giorni anomali sovrapposti contano una volta. Precisione/recall con denominatore nullo sono NaN. `--quick` è smoke (un servizio, due origini, 30 giorni anomalie), non benchmark completo. Report includono dettagli CSV, metadata e SVG senza dipendenze grafiche opzionali.

Le workflow sotto `.github/` diventano attive quando `cloudguard/` è esportato come repository autonomo; nella radice monorepo non sono workflow riconosciute da GitHub.
