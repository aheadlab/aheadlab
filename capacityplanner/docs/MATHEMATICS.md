# Dalla previsione al dimensionamento

## Segnale e perdita previsionale

Sia `B_t` il totale di byte osservati nell'ora. Il traffico medio è

`y_t = 8 B_t / (3600 × 10^6)` Mbit/s.

Per una previsione `p_t`, `MAE = mean(|y_t − p_t|)`. Il MASE divide questo
errore per `mean(|y_s − y_(s−168)|)` calcolato sul solo training dell'origine.
Se la scala è nulla il rapporto non è definito, non zero. Ogni giorno di test
è futuro rispetto al training; nessuna interpolazione attraversa il cutoff.

Una minore perdita previsionale non implica necessariamente minore costo
operativo: il secondo dipende da capacità discreta, asimmetria degli errori
e tempi di attivazione. Per questo si calcolano entrambi gli obiettivi.

## Margine comune

Sul periodo di calibrazione si osservano errori `e_t = y_t − p_t`.
Per un livello candidato `q`, il margine è `m_q = max(0, quantile_q(e))`.
Si usa la stessa regola per ogni modello, compresi quelli classici.
È una calibrazione empirica: non garantisce copertura futura in presenza di drift.

La capacità di un modulo `c` viene fissata usando il prefisso iniziale:
`c = percentile_95(training) / 10`. È un'unità normalizzata del simulatore,
non una risorsa fisica stimata dai dati. Il requisito pianificato è

`k_t = max(1, ceil((p_t + m_q) / c))`.

Con un'ora di attivazione, la prima ora del piano mantiene il valore precedente;
le ore successive ricevono il nuovo programma. Non si usa il traffico futuro
per impostare la capacità iniziale. I p90 del modello non vengono sommati.

## Contabilità delle risorse

- Capacità-ora: `C = Σ k_t`.
- Domanda normalizzata: `D = Σ y_t/c`.
- Deficit normalizzato: `U = Σ max(y_t/c − k_t, 0)`.
- Quota di domanda non coperta: `u = U/D`.
- Capacità inattiva: `I = Σ max(k_t − y_t/c, 0)`.

Identità verificabile: **`D − U + I = C`**. Il test software controlla questa
conservazione. Non si sostiene che il deficit corrisponda a pacchetti persi:
reti reali possono accodare il traffico e hanno dinamiche entro l'ora qui assenti.

Per confrontare due piani, il risparmio di capacità è
`S = 100 × (1 − C_AI/C_baseline)`.
Questa è una percentuale di moduli-ora nel simulatore, non di euro risparmiati.

## Scelta prima del test

Sul periodo di selezione si sceglie il margine meno costoso fra quelli con
`u <= 0,01`; anche modello AI e baseline vengono scelti qui. Se nessuna
configurazione soddisfa il vincolo, si sceglie la meno deficitaria e si dichiara
la non fattibilità. Il test successivo non cambia tali scelte.

Il criterio operativo è fissato nel [protocollo](PROTOCOL.md): almeno 10% di
capacità in meno, fattibilità e intervallo statistico favorevole, con margine
di non inferiorità sul deficit pari a 0,002 in valore assoluto.

Si ricampionano in modo accoppiato istituzioni e blocchi temporali di sette giorni.
Gli intervalli al 95% quantificano l'incertezza condizionata al campione; non
sono una dimostrazione causale o un teorema su qualsiasi infrastruttura futura.
