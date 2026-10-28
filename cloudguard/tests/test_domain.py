from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
from cloudguard.synthetic import genera_costi
from cloudguard.ingest import scarica_costi_aws
from cloudguard.prepare import tabella_giornaliera
from cloudguard.logic import stima_fine_mese, controlla_giorno
from cloudguard.notify import invia_telegram
from cloudguard.backtest import benchmark_forecast, anomaly_metrics, benchmark_anomalies
from cloudguard.daily import run_daily


def prediction(y, h):
    return SimpleNamespace(mediana=np.full(h, 10.), p10=np.full(h, 8.), p90=np.full(h, 12.),
                           p01=np.full(h, 5.), p99=np.full(h, 15.))


def series(end="2024-02-28", n=60):
    return pd.Series(10., index=pd.date_range(end=end, periods=n))


def test_synthetic():
    a, events = genera_costi()
    b, _ = genera_costi()
    pd.testing.assert_frame_equal(a, b)
    assert len(a) == 2000 and len(events) == 15
    assert (a.evento != "").sum() == events.giorni.sum()


@pytest.mark.parametrize("end,h", [("2024-02-28", 1), ("2023-02-27", 1), ("2024-02-27", 2)])
def test_month_leap_h1(end, h):
    calls = []
    def predict(y, horizon):
        calls.append(horizon)
        return prediction(y, horizon)
    result = stima_fine_mese(series(end), predictor=predict)
    assert calls == [h]
    assert result["stima"] == result["speso"]+h*10
    assert result["basso"] == result["speso"]+h*8


def test_month_end_no_model():
    def fail(*args):
        pytest.fail("model should not be called")
    result = stima_fine_mese(series("2024-02-29"), predictor=fail)
    assert result["stima"] == result["speso"] == 290


def test_alarm_no_leakage_and_provisional():
    s = series()
    s.iloc[-1] = 100
    def spy(history, h):
        assert len(history) == 59 and max(history) == 10 and h == 1
        return prediction(history, h)
    assert controlla_giorno(s, as_of="2024-03-01", predictor=spy)["anomalia"]
    assert not controlla_giorno(s, as_of="2024-02-29", predictor=spy)["valutato"]
    assert not controlla_giorno(s, as_of="2024-03-01", provisional_dates=[s.index[-1]], predictor=spy)["valutato"]


def test_ingest_pages_currency_estimated_empty():
    class Client:
        def __init__(self): self.calls = []
        def get_cost_and_usage(self, **kwargs):
            self.calls.append(kwargs)
            return dict(ResultsByTime=[dict(TimePeriod={"Start": "2024-02-01"}, Estimated=True,
                        Groups=[dict(Keys=["EC2"], Metrics={"UnblendedCost": {"Amount": "1.25", "Unit": "EUR"}})])],
                        **({"NextPageToken": "next"} if len(self.calls) == 1 else {}))
    client = Client()
    df = scarica_costi_aws(2, fine="2024-02-03", client=client)
    assert len(df) == 2 and df.valuta.eq("EUR").all() and df.estimated.all()
    assert client.calls[1]["NextPageToken"] == "next"
    assert client.calls[0]["TimePeriod"] == {"Start": "2024-02-01", "End": "2024-02-03"}
    empty = scarica_costi_aws(client=SimpleNamespace(get_cost_and_usage=lambda **k: {}))
    assert tabella_giornaliera(empty).empty
    assert run_daily(empty, as_of="2024-03-01") == []
    df.loc[0, "valuta"] = "USD"
    with pytest.raises(ValueError, match="valuta"):
        tabella_giornaliera(df)


def test_prepare_gaps_and_flags():
    raw, _ = genera_costi()
    raw = raw[raw.servizio == "Amazon EC2"].copy()
    missing = raw.data.iloc[40]
    raw = raw[raw.data != missing]
    raw.loc[raw.index[-1], "estimated"] = True
    table = tabella_giornaliera(raw)
    assert table.loc[missing].iloc[0] == 0
    assert len(table.attrs["provisional_dates"]) == 1
    with pytest.raises(ValueError):
        stima_fine_mese(series().iloc[[0, 2, 3]])


def test_rolling_prefix_only():
    s = pd.Series(np.arange(100.), index=pd.date_range("2024-01-01", periods=100))
    calls = []
    def spy(y, h):
        assert np.array_equal(y, np.arange(len(y)))
        calls.append((len(y), h))
        return np.repeat(y[-1], h)
    frame = benchmark_forecast(s.to_frame("EC2"), model="mock", folds=2, horizons=(7,), predictor=spy)
    assert calls == [(93, 7), (86, 7)] and len(frame) == 6
    assert frame.coverage80.isna().all()


def test_anomaly_denominator_intersection_not_all_events():
    evaluated = pd.DataFrame(dict(servizio=["A"]*3, data=pd.date_range("2024-01-02", periods=3), anomalia=[True, False, True]))
    events = pd.DataFrame([dict(servizio="A", inizio=pd.Timestamp("2024-01-01"), giorni=3),
                           dict(servizio="A", inizio=pd.Timestamp("2023-01-01"), giorni=1),
                           dict(servizio="B", inizio=pd.Timestamp("2024-01-02"), giorni=1)])
    m = anomaly_metrics(evaluated, events)
    assert m["eventi_valutati"] == m["eventi_trovati"] == 1
    assert m["precisione"] == m["recall_giorni"] == .5
    assert m["recall_eventi"] == 1 and m["falsi_allarmi"] == 1
    empty = anomaly_metrics(evaluated.iloc[:0], events)
    assert empty["eventi_valutati"] == 0 and np.isnan(empty["recall_eventi"])


def test_anomaly_backtest_daily_prefix():
    s = series(n=70)
    calls = []
    def spy(y, h):
        calls.append(len(y))
        return prediction(y, h)
    events = pd.DataFrame(columns=["servizio", "inizio", "giorni"])
    summary, detail = benchmark_anomalies(s.to_frame("A"), events, model="mock", days=3, predictor=spy)
    assert calls == [67, 68, 69] and len(detail) == 6
    assert summary.giorni_valutati.eq(3).all()


def test_notify_dryrun_and_sanitized(monkeypatch):
    assert invia_telegram("hello")["dry_run"]
    monkeypatch.setenv("TELEGRAM_TOKEN", "secret-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    def bad(*args, **kwargs):
        assert kwargs["timeout"] == 15
        raise RuntimeError("secret-token")
    with pytest.raises(RuntimeError) as exc:
        invia_telegram("hello", send=True, session=SimpleNamespace(post=bad))
    assert "secret-token" not in str(exc.value)
