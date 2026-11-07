"""Bounded local build/browser helpers; only the new Capacity Planner project."""
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]


def run(command):
    subprocess.run(command,check=True,cwd=ROOT)


phase=sys.argv[1]
if phase=='web':
    run(['docker','run','--rm','--network','none','--memory','1g','--memory-swap','1g','--cpus','1',
        '--mount',f'type=bind,source={ROOT / "web"},target=/web',
        '--mount','type=volume,source=aheadlab-stocksense-browser-node,target=/seed,readonly',
        '--mount','type=volume,source=aheadlab-capacity-node,target=/web/node_modules',
        '-w','/web','node:22-bookworm-slim','sh','-c','cp -a /seed/. /web/node_modules/ && npm run build'])
elif phase=='browser':
    run(['docker','run','--rm','--network','capacityplanner_default','--memory','1g','--memory-swap','1g','--cpus','1',
        '--shm-size','256m','--mount',f'type=bind,source={ROOT / "web"},target=/web',
        '--mount','type=volume,source=aheadlab-capacity-node,target=/web/node_modules',
        '-e','BASE_URL=http://capacityplanner:8501','-w','/web',
        'mcr.microsoft.com/playwright:v1.56.1-noble','npx','playwright','test'])
elif phase=='build':
    run(['docker','compose','build'])
elif phase=='up':
    run(['docker','compose','up','-d','--no-deps','--wait','--wait-timeout','120','capacityplanner'])
elif phase=='verify':
    run([sys.executable,str(ROOT/'scripts/check_live.py')])
else:
    raise ValueError(phase)
