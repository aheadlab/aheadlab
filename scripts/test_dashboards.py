"""Run Chromium desktop/mobile tests against the three running web applications."""
import argparse
import json
from pathlib import Path
import subprocess
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models', action='store_true', help='Also exercise real 5M inference over HTTP')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    for project, port in [('cloudguard', 8501), ('stocksense', 8502), ('solarcast', 8503)]:
        container = subprocess.check_output(
            ['docker', 'compose', 'ps', '-q', project], cwd=root, text=True).strip()
        if not container:
            raise SystemExit(f'{project}: start applications with docker compose up -d first')
        info = json.loads(subprocess.check_output(['docker', 'inspect', container], text=True))[0]
        network = next(iter(info['NetworkSettings']['Networks']))
        subprocess.run([
            'docker', 'run', '--rm', '--ipc=host', '--network', network,
            '-e', f'BASE_URL=http://{project}:8501',
            '-v', f'{(root/project/"web").as_posix()}:/work',
            '-v', f'aheadlab-{project}-browser-node:/work/node_modules',
            '-w', '/work', 'mcr.microsoft.com/playwright:v1.56.1-noble',
            'sh', '-c', 'npm ci --no-audit --no-fund && npx playwright test',
        ], check=True)
        if args.models:
            payload = {'model': '5M'}
            if project == 'stocksense':
                payload['top_n'] = 2
            if project == 'solarcast':
                payload['method'] = 'B'
            request = urllib.request.Request(
                f'http://127.0.0.1:{port}/api/forecast',
                data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(request, timeout=600) as result:
                body = json.load(result)
            assert body['model'] == '5M', body
            assert body.get('forecast') or body.get('products'), body
            print(f'{project}: real 5M API inference PASS')


if __name__ == '__main__':
    main()
