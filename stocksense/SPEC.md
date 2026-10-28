---
id: stocksense-contract
type: module-design
status: draft
title: StockSense — domanda e scorte
---

# StockSense — domanda e scorte

Le API di backtest e simulazione verificano date ordinate, univoche e giornaliere consecutive; un RangeIndex a passo uno rappresenta osservazioni giornaliere senza date. Questo impedisce di confondere lead time in giorni con righe settimanali, o di usare training cronologicamente futuro. La cache dashboard include l'impronta SHA256 del file UCI corrente, calcolata prima della cache: una sostituzione del file invalida anche dati e ordini della UI, non solo il parquet.

La media geometrica MASE è zero quando almeno un caso ha errore esattamente zero. Non indica previsioni perfette sugli altri casi: per interpretare i report usare anche MAE, vittorie e le righe per SKU/origine.

Il prodotto autonomo trasforma transazioni Online Retail II in previsioni giornaliere e proposte di riordino. La demo sintetica non si presenta come UCI; le giacenze sono sempre simulate o fornite esplicitamente, mai dedotte come reali dalle transazioni.

La selezione top SKU è congelata sul prefisso prima del primo test. I calendari conservano gli zeri; cancellazioni, quantità/prezzi non positivi e codici non prodotto sono esclusi. Il percentile 99,5 per limitare outlier è appreso da ogni training e applicato solo all'input del modello; target e metriche restano sulle vendite originali.

Il riordino copre lead time più ciclo, considera giacenza e ordini in arrivo, tronca previsioni negative e richiede un orizzonte sufficiente. Lotto minimo è una quantità minima, non un multiplo. Sommare quantili giornalieri produce una regola euristica, non un livello di servizio garantito. Previsioni puntuali baseline non diventano finti intervalli calibrati.

La simulazione parte dallo stesso stock per tutti i metodi, riceve gli ordini alla data prevista, rivede gli ordini a cadenza settimanale usando solo il passato, poi consuma le vendite reali e registra vendite perse senza arretrati. Le metriche pubblicano giorni di stockout, vendite perse e giacenza media. Tempi di consegna e ciclo devono essere interi positivi. Benchmark rolling 30 giorni, 8 origini passo 30, MASE settimanale, media geometrica e vittorie; serie costanti non hanno MASE definito.

## Convenzioni implementative
La CLI parte offline con dati sintetici seed 42 (50 prodotti); UCI e Timestral sono opt-in espliciti. `--model baseline` confronta tutte le tre baseline, una taglia aggiunge Timestral allo stesso confronto. Full: 8 fold, orizzonte/passo 30, top 50, inventario ultimi 180 giorni. Smoke: 2 SKU, 2 fold orizzonte/passo 28, inventario 28 giorni. La selezione è congelata prima del più antico cutoff tra backtest e simulazione.

La giornata simulata riceve gli ordini, rivede la posizione prima di osservare la domanda del giorno, consuma e registra lo stock finale. Gli ordini del giorno t arrivano a t + lead time; la posizione include tutti gli ordini pendenti. Primo review al primo giorno valutato, poi ogni ciclo (default 7). Stock iniziale: totale ultime 21 giornate training per fattore uniforme [0,3; 2], seed 42, comune ai metodi. La media di giacenza è per SKU-giorno a fine giornata, i giorni stockout sono sommati sui SKU. Gli ordini ancora pendenti alla fine restano nel registro, non arrivano anticipatamente.

CSV config: riga `*` default, override SKU; livelli 0,5/0,9/0,99. Baseline senza quantili usa solo previsione puntuale e scorta sicurezza zero, dichiarandolo. Vittorie: ogni minimo ex aequo conta; MASE indefiniti esclusi; media geometrica zero se un caso valido è zero. La dashboard mostra data effettiva della decisione, non spaccia lo storico per dati odierni, e la curva di stock è senza nuovi arrivi. CI locale al repository esportabile: workflow in `.github/workflows/` attivo quando stocksense è radice del repository.
