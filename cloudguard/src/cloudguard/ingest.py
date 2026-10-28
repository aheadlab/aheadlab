"""AWS is opt-in: invoking this function explicitly may incur API charges."""
from datetime import date, timedelta
import pandas as pd

COLUMNS = ["data", "servizio", "costo", "valuta", "estimated"]


def scarica_costi_aws(giorni=400, *, fine=None, client=None):
    if isinstance(giorni, bool) or not isinstance(giorni, int) or giorni < 1:
        raise ValueError("giorni deve essere positivo")
    end = pd.Timestamp(fine or date.today()).date()
    if client is None:
        import boto3
        client = boto3.client("ce", region_name="us-east-1")
    rows, token, seen = [], None, set()
    reported_dates, estimated_dates = set(), set()
    while True:
        kwargs = dict(TimePeriod={"Start": (end-timedelta(days=giorni)).isoformat(), "End": end.isoformat()},
                      Granularity="DAILY", Metrics=["UnblendedCost"],
                      GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}])
        if token:
            kwargs["NextPageToken"] = token
        response = client.get_cost_and_usage(**kwargs)
        for day in response.get("ResultsByTime", []):
            day_date = pd.Timestamp(day["TimePeriod"]["Start"])
            reported_dates.add(day_date)
            if day.get("Estimated", False):
                estimated_dates.add(day_date)
            for group in day.get("Groups", []):
                metric = group["Metrics"]["UnblendedCost"]
                rows.append(dict(data=pd.Timestamp(day["TimePeriod"]["Start"]), servizio=group["Keys"][0],
                                 costo=float(metric["Amount"]), valuta=metric["Unit"],
                                 estimated=day.get("Estimated", False)))
        token = response.get("NextPageToken")
        if not token:
            break
        if token in seen:
            raise ValueError("AWS pagination token ripetuto")
        seen.add(token)
    frame = pd.DataFrame(rows, columns=COLUMNS)
    frame.attrs['reported_dates'] = sorted(reported_dates)
    frame.attrs['estimated_dates'] = sorted(estimated_dates)
    return frame
