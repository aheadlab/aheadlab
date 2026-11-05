---
id: aheadlab-architecture
type: architecture-design
title: Confini dei tre repository
parent: aheadlab-goals
status: draft
---
# Architettura

`cloudguard/`, `stocksense/`, `solarcast/` sono repository esportabili, senza dipendenze runtime fra loro. Ogni package usa layout src, backend FastAPI, frontend React/TypeScript, script CLI, test e Dockerfile locali. Docker Compose nella radice è solo una comodità di sviluppo.

## Confine web
Ogni frontend dipende solo dall'API del proprio progetto: i componenti comuni sono copie locali, non un package condiviso a runtime. Docker compila il frontend con Node e serve gli asset statici dalla stessa origine FastAPI; il processo Python non richiede Node. Questo conserva l'esportabilità dei repository e separa l'interazione browser dalla logica previsionale già testata.

Le API sono workspace locali senza autenticazione, esposte solo su loopback nella configurazione fornita. Uvicorn usa un processo: il limite di un calcolo concorrente è per processo, con risposta 409 anziché accodamento illimitato. La cancellazione del fetch non interrompe un'inferenza in corso. Parametri fuori contratto sono rifiutati; errori upstream non espongono dettagli sensibili e valori numerici non finiti diventano null. I report sono identificati tramite un registro delle cartelle risultati, mai tramite percorsi arbitrari del client. I dettagli giornalieri voluminosi di inventario e anomalie restano artefatti locali.

Le impostazioni UI persistono nel browser, non costituiscono stato multiutente. Errori e ricalcoli non trasformano i risultati precedenti in nuove previsioni; parametri non applicati sono segnalati. Test HTTP verificano i contratti e test Chromium esercitano i flussi desktop/mobile, oltre ai test di dominio e modello.

## Modelli e valutazione
Timestral è importato solo in `forecaster.py`; la libreria ufficiale è fissata al commit `a534bdbd244d64f3d9d743f46c7bf6fc330ed4ff`. Il contratto restituisce cinque vettori 1D ordinati, anche per un singolo passo. L'input è copiato prima del modello per accettare array read-only (per esempio da pandas) senza condividerne memoria modificabile con PyTorch. Gli errori non causano fallback silenziosi. Le baseline sono esplicitamente nominate. Test unitari senza rete e test di integrazione con pesi reali restano distinti.

Il backtest usa solo il prefisso temporale per fit, clipping e selezione. Gli intervalli ottenuti sommando quantili marginali sono euristiche: non hanno copertura nominale garantita e non sono necessariamente prudenti. MASE non definito su storico costante è NaN, non zero. Risultati sintetici, smoke e benchmark completo sono etichettati separatamente.

## Confini dominio
CloudGuard conserva la valuta AWS e non mescola valute; esclude dati recenti provvisori dagli allarmi. Nessuna chiamata AWS o invio Telegram automatico nella demo.
StockSense distingue domanda osservata, giacenza simulata e arrivi già ordinati. La selezione SKU e il percentile 99,5 sono calcolati sul training; il target del test resta grezzo. Gli ordini arrivano dopo il lead time e le vendite perse non diventano arretrati.
SolarCast mantiene indice orario UTC e produzione normalizzata kWh/kWp; scala per potenza solo nel prodotto. Il meteo osservato futuro nei backtest è dichiarato oracle/limite superiore, non una previsione realmente disponibile. Le fasce sono intervalli semiaperti e includono correttamente l'ultima ora.

## Stato delle verifiche esterne
Docker Linux disponibile con circa 23,5 GiB RAM. API upstream verificata nel README e sorgente: input (B,V,T), `known_covariates` (B,C,T+H), output (B,V,H); quantili non supportati causano ValueError. Cache Hugging Face standard. Licenza pesi consultata: limite di fatturato consolidato **mensile** superiore a 20 milioni USD nel mese precedente. Endpoint PVGIS v5_3 risponde per 2023; i dati restano simulazioni satellitari.
