from types import SimpleNamespace
import pandas as pd
from cloudguard.ingest import scarica_costi_aws
from cloudguard.prepare import tabella_giornaliera
from cloudguard.daily import run_daily


def test_empty_aws_groups_keep_provisional_day():
    dates = pd.date_range('2024-01-01', periods=70)
    days = []
    for i, date in enumerate(dates):
        groups = [] if i == 50 else [dict(Keys=['EC2'], Metrics={'UnblendedCost': {'Amount': '10', 'Unit': 'USD'}})]
        days.append(dict(TimePeriod={'Start': str(date.date())}, Estimated=i == 50, Groups=groups))
    client = SimpleNamespace(get_cost_and_usage=lambda **kwargs: {'ResultsByTime': days})
    raw = scarica_costi_aws(client=client)
    table = tabella_giornaliera(raw)
    assert dates[50] in table.attrs['provisional_dates']
    result = run_daily(raw, as_of=dates[-1]+pd.Timedelta(days=2))
    assert len(result) == 1
    assert not result[0]['valutato']


def test_service_eligibility_uses_only_training_dates():
    dates = pd.date_range('2024-01-01', periods=90)
    raw = pd.DataFrame(dict(data=dates, servizio='NEW', costo=10., valuta='USD', estimated=False))
    assert tabella_giornaliera(raw).shape[1] == 1
    assert tabella_giornaliera(raw, selection_end=dates[58]).shape[1] == 0
    assert run_daily(raw, as_of=dates[59]+pd.Timedelta(days=2)) == []
