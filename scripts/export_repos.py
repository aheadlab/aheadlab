"""Copy the three repositories without ignored datasets, caches or local secrets."""
import argparse
from pathlib import Path
import shutil
import subprocess

PROJECTS = ('cloudguard', 'stocksense', 'solarcast')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='New directory outside this workspace')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    target = args.output.resolve()
    if target == root or root in target.parents:
        parser.error('Output must be outside the workspace')
    if target.exists():
        parser.error('Output already exists; nothing overwritten')
    files = subprocess.check_output(
        ['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard', '--', *PROJECTS],
        cwd=root).decode('utf-8').split('\0')
    selected = sorted(set(name for name in files if name))
    if not selected:
        parser.error('No project files found')
    for name in selected:
        source = root / name
        if source.is_symlink() or not source.is_file():
            parser.error(f'Expected regular source file: {name}')
    target.mkdir(parents=True)
    for name in selected:
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / name, destination)
    print(f'Exported {len(selected)} files to {target}')
    print('No remote repositories created and no git history copied.')


if __name__ == '__main__':
    main()
