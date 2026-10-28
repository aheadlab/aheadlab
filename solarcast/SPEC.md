---
id: solarcast-contract
type: module-design
status: draft
title: SolarCast — energia e fasce orarie
---

# SolarCast — energia e fasce orarie

Pipeline autonoma di previsione fotovoltaica a 48 ore. Indici orari UTC univoci e ordinati; Europe/Rome solo per visualizzazione. Produzione interna normalizzata in kWh/kWp: si richiede PVGIS a 1 kWp e si scala una sola volta nel prodotto. P in watt è convertito in energia oraria approssimata dividendo per 1000, non una misurazione di energia integrata. PVGIS è simulato, non produzione reale.

Timestral A usa solo storico; B usa covariate storiche e future allineate (radiazione, nuvole, temperatura). Il wrapper è l'unico contatto con la libreria. Baseline: persistenza 24 ore e regressione lineare su radiazione stimata solo sugli ultimi 30 giorni di training. Non si inventano intervalli probabilistici per i modelli puntuali. Le previsioni negative sono troncate a zero.

Backtest rolling a mezzanotte UTC, orizzonte 48h, metriche giornaliere in kWh/kWp, orarie diurne, copertura e suddivisione per stagione/tipo di cielo. Il meteo osservato futuro è etichettato oracle: confronto ottimistico non operativo. Il contesto massimo e il sottoinsieme di origini usati sono registrati nel report; smoke non è presentato come un anno completo. Missing target non è uno zero; metriche filtrano osservazioni mancanti esplicitamente.

Fasce consigliate: p10 per kWp scalato per potenza, soglia in kW, blocchi contigui almeno della durata richiesta; fine esclusiva un'ora oltre l'ultimo campione. Quantità energetica del blocco dalla mediana. La durata è tempo trascorso anche nel cambio DST. Con baseline senza p10 le fasce restano indicative e non vengono chiamate prudenti.

Cache dati indicizzata da tutti i parametri della richiesta, incluse geometria impianto, periodo e località. Dati reali pubblici e demo sintetica sono separati e nominati. Meteo storico non può essere collegato alla previsione attuale come se fosse contiguo allo storico PVGIS: l'uso operativo richiede storico produzione recente fornito dall'utente. Telegram dry-run di default; nessuna pubblicazione o invio implicito.
