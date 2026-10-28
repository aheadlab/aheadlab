"""Run isolated repository tests using their production Docker images."""
import argparse
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models', action='store_true', help='Download and test real Timestral 5M')
    parser.add_argument('--build', action='store_true', help='Build all images before testing')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.build:
        subprocess.run(['docker', 'compose', 'build'], cwd=root, check=True)
    for project in ('cloudguard', 'stocksense', 'solarcast'):
        command = ['docker', 'compose', 'run', '--rm', '--no-deps', '-e',
                   f'RUN_MODEL_TESTS={int(args.models)}', project, 'pytest', '-q']
        print(f'\n=== {project} ===', flush=True)
        subprocess.run(command, cwd=root, check=True)


if __name__ == '__main__':
    main()
