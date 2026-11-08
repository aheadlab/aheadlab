# Risultati V2 generati dagli artefatti

Confronto primario congelato sulla selezione: 28M / adaptive contro ets / adaptive.

| Misura | AI selezionata | Alternativa classica selezionata |
|---|---:|---:|
| Moduli-ora | 1.679.669 | 1.659.699 |
| Deficit normalizzato | 1,540% | 1,496% |
| Deficit sul traffico grezzo | 0,673% | 0,651% |

Riduzione di capacità AI: **-1,20%**, intervallo al 95% [-5,44; 2,46]%. Differenza di deficit, intervallo al 95% [-0,032; 0,206] punti percentuali.

**Criterio primario non soddisfatto.**

## Tutte le politiche selezionate

| Modello | Politica | Moduli-ora | Deficit | Istituzioni oltre 5% |
|---|---|---:|---:|---:|
| last | original | 2.061.411 | 1,297% | 2 |
| last | adaptive | 1.750.497 | 1,528% | 1 |
| daily | original | 2.061.568 | 1,264% | 2 |
| daily | adaptive | 1.748.873 | 1,552% | 1 |
| weekly | original | 1.977.500 | 2,280% | 3 |
| weekly | adaptive | 1.723.411 | 1,528% | 1 |
| weekly_mean | original | 1.862.105 | 2,079% | 1 |
| weekly_mean | adaptive | 2.382.254 | 0,911% | 1 |
| ets | original | 1.969.567 | 1,261% | 2 |
| ets | adaptive | 1.659.699 | 1,496% | 1 |
| mstl | original | 1.910.295 | 1,245% | 2 |
| mstl | adaptive | 2.374.040 | 0,916% | 1 |
| ridge | original | 1.968.731 | 1,402% | 2 |
| ridge | adaptive | 1.680.502 | 1,531% | 1 |
| 5M | original | 1.991.169 | 1,325% | 3 |
| 5M | adaptive | 1.685.864 | 1,546% | 1 |
| 28M | original | 1.991.840 | 1,305% | 3 |
| 28M | adaptive | 1.679.669 | 1,540% | 1 |
| reactive_only | reactive | 610.191 | 10,796% | 19 |
| fixed_p99 | fixed | 1.436.736 | 8,191% | 4 |

Confronti secondari descrittivi: nessuna sostituzione dei vincitori dopo il test.
