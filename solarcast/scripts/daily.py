"""Safe daily demo: always dry-run, never reads credentials or sends messages."""
from solarcast.demo import synthetic
from solarcast.forecast import forecast
from solarcast.logic import fasce_migliori
from solarcast.notify import telegram


def main():
    data = synthetic()
    result = forecast(data.iloc[:-48], data.iloc[-48:].drop(columns='kwh'))
    blocks = fasce_migliori(result.frame['median'], None, result.frame.index, 6)
    message = 'SolarCast DEMO sintetica retrospettiva — 6 kWp\nFasce indicative (nessun p10):\n'
    message += '\n'.join(f"{b['start']} – {b['end']} (fine esclusiva): {b['expected_kwh']:.1f} kWh" for b in blocks)
    print(telegram(message))


if __name__ == '__main__':
    main()
