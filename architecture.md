---
id: aheadlab-architecture
type: architecture-design
title: Confini dei tre repository
parent: aheadlab-goals
status: draft
---
# Architettura

`cloudguard/`, `stocksense/`, `solarcast/` sono repository esportabili, senza dipendenze runtime fra loro. Ogni package usa layout src, dashboard Streamlit, script CLI, test e Dockerfile locali. Docker Compose nella radice è solo una comodità di sviluppo.

## Modelli e valutazione
Timestral è importato solo in `forecaster.py`; la libreria ufficiale è fissata al commit `a534bdbd244d64f3d9d743f46c7bf6fc330ed4ff`. Il contratto restituisce cinque vettori 1D ordinati, anche per un singolo passo. L'input è copiato prima del modello per accettare array read-only (per esempio da pandas) senza condividerne memoria modificabile con PyTorch. Gli errori non causano fallback silenziosi. Le baseline sono esplicitamente nominate. Test unitari senza rete e test di integrazione con pesi reali restano distinti.

Il backtest usa solo il prefisso temporale per fit, clipping e selezione. Gli intervalli ottenuti sommando quantili marginali sono euristiche: non hanno copertura nominale garantita e non sono necessariamente prudenti. MASE non definito su storico costante è NaN, non zero. Risultati sintetici, smoke e benchmark completo sono etichettati separatamente.

## Confini dominio
CloudGuard conserva la valuta AWS e non mescola valute; esclude dati recenti provvisori dagli allarmi. Nessuna chiamata AWS o invio Telegram automatico nella demo.
StockSense distingue domanda osservata, giacenza simulata e arrivi già ordinati. La selezione SKU e il percentile 99,5 sono calcolati sul training; il target del test resta grezzo. Gli ordini arrivano dopo il lead time e le vendite perse non diventano arretrati.
SolarCast mantiene indice orario UTC e produzione normalizzata kWh/kWp; scala per potenza solo nel prodotto. Il meteo osservato futuro nei backtest è dichiarato oracle/limite superiore, non una previsione realmente disponibile. Le fasce sono intervalli semiaperti e includono correttamente l'ultima ora.

## Stato delle verifiche esterne
Docker Linux disponibile con circa 23,5 GiB RAM. API upstream verificata nel README e sorgente: input (B,V,T), `known_covariates` (B,C,T+H), output (B,V,H); quantili non supportati causano ValueError. Cache Hugging Face standard. Licenza pesi consultata: limite di fatturato consolidato **mensile** superiore a 20 milioni USD nel mese precedente. Endpoint PVGIS v5_3 risponde per 2023; i dati restano simulazioni satellitari.
