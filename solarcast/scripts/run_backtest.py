"""Run from the standalone project: python scripts/run_backtest.py --quick."""
import argparse
from solarcast.backtest import run_backtest, save_results
from solarcast.demo import synthetic
from solarcast.ingest import historical_dataset


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', choices=['synthetic', 'pvgis'], default='synthetic')
    parser.add_argument('--model', choices=['baseline', '5M', '28M', '209M'], default='baseline')
    parser.add_argument('--quick', action='store_true')
    parser.add_argument('--output', default='results/backtest')
    parser.add_argument('--year', type=int, default=2023)
    parser.add_argument('--lat', type=float, default=45.82)
    parser.add_argument('--lon', type=float, default=8.83)
    parser.add_argument('--angle', type=float, default=30)
    parser.add_argument('--aspect', type=float, default=0)
    parser.add_argument('--loss', type=float, default=14)
    parser.add_argument('--max-context', type=int)
    parser.add_argument('--cache-dir', default='data/raw')
    args = parser.parse_args()
    if args.quick and args.max_context is not None and args.max_context > 720:
        parser.error('--quick context must be <=720')
    data = synthetic(args.year) if args.data == 'synthetic' else historical_dataset(
        args.lat, args.lon, args.year, args.angle, args.aspect, args.loss, args.cache_dir)
    daily, summary, metadata = run_backtest(data, args.model, args.quick, args.max_context, args.data)
    metadata['request'] = vars(args)
    save_results(daily, summary, metadata, args.output)
    print(summary.to_string(index=False))


if __name__ == '__main__':
    main()
