# Dalla previsione all'orario: formule e controlli

Un lavoro richiede energia totale E kWh, distribuita uniformemente su d ore
consecutive. La scadenza è H ore. Nel benchmark d=4, H=96, E=100; cambiare
E scala i kg ma non cambia la scelta o la percentuale di vantaggio.

Per ciascun possibile inizio s=0,...,H−d:

```text
intensità prevista del lavoro(s) = (1/d) × somma(previsione[s:s+d])
s* = argmin intensità prevista del lavoro(s)
kg attribuiti(s*) = E / (1000 × d) × somma(intensità osservata[s*:s*+d])
```

Le finestre hanno tutte la stessa durata e lo stesso consumo. L'osservato
compare soltanto nella verifica finale; non decide s*. A parità numerica
(tolleranza assoluta 1e−10) si sceglie l'inizio più vicino. Poiché l'insieme
degli inizi è finito, enumerarlo trova il minimo esatto del problema dato
il vettore di previsione. Questo non dimostra che la previsione sia corretta.

Invarianti verificati: s*>=0, s*+d<=H, esattamente d ore attive, energia
totale E. Non vengono scelte ore sparse. Nessun lavoro viene eliminato.
Il modello di simulazione non include concorrenza fra lavori, limiti di
rete, variazioni di potenza, prezzi o costi dell'attesa.

La media dei kg sulle stesse coppie zona/giorno confronta i metodi:

```text
riduzione (%) = 100 × (1 − media(kg_AI) / media(kg_baseline))
```

Non si fa la media di percentuali per casi con denominatori diversi. Le sei
zone primarie hanno lo stesso peso, e ogni caso usa la stessa energia. La
differenza in g/kWh è numericamente uguale ai kg per MWh: 0,1438 g/kWh
corrisponde a 0,1438 kg/MWh, cioè circa 144 grammi per MWh.

Il regret è la differenza rispetto alla finestra migliore individuata
conoscendo tutto il futuro. L'oracolo è soltanto un limite ideale: non è
disponibile in esercizio e non viene usato per selezionare la baseline.

Incertezza: 5.000 bootstrap accoppiati di blocchi circolari da sette giorni,
con tutte le zone ricampionate insieme e seed 20261109. Si ricampiona il
giorno, non ogni ora come osservazione indipendente; gli orizzonti si
sovrappongono. Il confronto a blocchi 14 giorni è informativo solo sul
periodo di 176 giorni. Con 14 osservazioni e un blocco lungo 14, ogni
campione contiene tutta la serie e l'intervallo diventa degenere: il suo
valore meccanico nel JSON originale non deve essere interpretato come
incertezza. La dashboard lo esclude e il report usa l'intervallo a 7 giorni.

La verifica statistica è evidenza sul campione. Nessuna formula garantisce
la superiorità generale di Timestral. L'intensità della fonte è basata sul
mix di produzione: questi kg sono attribuiti secondo quel metodo, non una
misurazione delle emissioni marginali causalmente evitate spostando un carico.
