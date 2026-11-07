# Esperimenti isolati

Piano e vincoli: [../VALIDAZIONE.md](../VALIDAZIONE.md).
Esiti e interpretazione: [RESULTS.md](RESULTS.md).

Gli script non sono importati dalle applicazioni. I frontend continuano a usare
i risultati originali nelle proprie cartelle `results/`.

## Esecuzione Windows / Docker Desktop

Prerequisiti: immagini locali `aheadlab-cloudguard`, `aheadlab-stocksense`,
`aheadlab-solarcast`; volume esistente `aheadlab_model-cache` con snapshot 5M
`bdd20cfc15a3fea0e4cb5ccef37f8d3ca7aa335f`; Excel/parquet UCI e quattro risposte
PVGIS/Open-Meteo nelle cartelle dati originali. Nessun download automatico.

```powershell
python validation/run.py test-cloudguard test-stocksense test-solarcast audit solar stock cloud
python validation/check_results.py
```

Il runner limita ciascun container a 2 GiB, 1 CPU, zero swap aggiuntivo e nessuna
rete. Non pubblica porte. Si rifiuta di iniziare con meno di 5 GiB disponibili
sull'host e ferma solo il proprio container se la disponibilità scende sotto
4 GiB. La memoria host è campionata ogni 5 secondi. Questi limiti riducono il
carico, ma non garantiscono assenza assoluta di interferenza su disco/kernel.

Le suite escludono i test di integrazione marcati per download; l'esperimento
StockSense e quello CloudGuard fanno comunque inferenza reale sullo snapshot
fissato. SolarCast riutilizza le previsioni AI già pubblicate, ricalcola quattro
regressioni e verifica la riproduzione della baseline originale.

## Protocollo

- StockSense: 50 SKU scelti sul prefisso, 8 finestre da 30 giorni. Modelli:
  Timestral 5M, AutoETS, mediana mobile 28 giorni, Croston-SBA. Winsorization
  99,5% sul solo training identica fra metodi. Si confrontano anche errore
  cumulato a 30 giorni e bias, non soltanto MAE.
- Inventario: 180 giorni, lead time 14, revisione 7. Target = somma delle
  previsioni puntuali a 21 giorni + max(0, quantile degli errori cumulati).
  Sei finestre precedenti al test, non sovrapposte; calibrazione congelata.
  Quantili 0,5/0,8/0,9 per tutti, senza usare p90 marginali dell'AI. Ogni modello
  riceve la stessa domanda e la stessa giacenza iniziale. Il bootstrap non
  trasforma questi scenari in una prova causale del profitto.
- SolarCast: regressioni radiazione / tutte le tre covariate, con 720 / 8784
  ore di training. È un'analisi fattoriale esplorativa; non si dichiara vincitore
  un parametro scelto dopo aver visto il test. Confronti separati per giorno 1/2.
- CloudGuard: tre seed, tre servizi, 360 giorni. Picco 1,7x per tre giorni,
  deriva dal 5 al 45% in 21 giorni, aumento pianificato permanente del 25%.
  L'aumento pianificato non è comunicato a nessun rilevatore: il test mostra
  anche il limite di un allarme basato soltanto sullo storico.
- Intervalli esplorativi al 95%: 2000 bootstrap, seed fisso; cluster per SKU
  sul retail, blocchi circolari di 7/28 origini sul solare. Il primo non copre
  shock comuni al singolo negozio, il secondo non prova generalizzazione ad
  altri impianti/anni. I MAE diurni nel bootstrap pesano ugualmente i giorni;
  le tabelle aggregate pesano il numero di ore diurne, come il report originale.

Gli output dettagliati d'inventario e le istantanee dei container restano locali
e ignorati da Git. Le tabelle riassuntive, gli score accoppiati, gli hash e i log
di verifica sono conservabili con il codice. Rieseguire una fase sostituisce i
suoi risultati; i report applicativi originali sono sempre montati read-only.

## Verifiche degli artefatti

`check_results.py` verifica completezza delle coppie SKU/fold, riproduzione dei
400 errori 5M originali, domanda identica nei dodici scenari e conservazione
dell'inventario con arrivi ritardati. Non certifica l'adeguatezza commerciale.
