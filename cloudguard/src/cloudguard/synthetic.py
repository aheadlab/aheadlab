"""Riproducibile, senza dipendere dall'orologio o dalla rete."""
import numpy as np
import pandas as pd

END_DATE = "2025-12-31"


def genera_costi(giorni=400, seed=7, fine=END_DATE):
    if isinstance(giorni, bool) or not isinstance(giorni, int) or giorni < 60:
        raise ValueError("giorni deve essere un intero >= 60")
    dates = pd.date_range(end=pd.Timestamp(fine).normalize(), periods=giorni)
    rng = np.random.default_rng(seed)
    t = np.arange(giorni)
    services = {"Amazon EC2": (40, .03, -.25, .06), "Amazon RDS": (18, .01, -.05, .03),
                "Amazon S3": (6, .01, 0, .04), "AWS Lambda": (3, .005, -.4, .15),
                "CloudWatch": (2, .002, 0, .10)}
    rows, events = [], []
    for service, (base, trend, weekend, noise) in services.items():
        y = (base + trend*t) * (1 + weekend*(dates.dayofweek >= 5)) * rng.lognormal(0, noise, giorni)
        labels = np.full(giorni, "", dtype=object)
        # One event per disjoint time block prevents ambiguous overlapping labels.
        for k, block in enumerate(np.array_split(np.arange(30, giorni-3), 3)):
            i, duration = int(rng.choice(block)), int(rng.integers(1, 4))
            duration = min(duration, int(block[-1])-i+1)
            event = f"{service}-{k+1}"
            y[i:i+duration] *= rng.uniform(3, 6)
            labels[i:i+duration] = event
            events.append(dict(evento=event, servizio=service, inizio=dates[i], giorni=duration))
        rows.append(pd.DataFrame(dict(data=dates, servizio=service, costo=y.round(2),
                                     valuta="USD", estimated=False, evento=labels)))
    return pd.concat(rows, ignore_index=True), pd.DataFrame(events)
