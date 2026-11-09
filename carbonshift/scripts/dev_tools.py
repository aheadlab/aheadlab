"""Build and preview only CarbonShift; never restart another Compose project."""
from pathlib import Path
import subprocess,sys
from run_isolated import ram
ROOT=Path(__file__).resolve().parents[1]
def run(args):subprocess.run(args,cwd=ROOT,check=True)
phase=sys.argv[1]
if phase!='stop' and ram()<5:raise RuntimeError('Need 5 GiB host RAM reserve')
compose=['docker','compose','-f','compose.yaml','-f','compose.local.yaml']
if phase=='web':
    run(['docker','run','--rm','--network','none','--memory','1g','--memory-swap','1g','--cpus','1',
        '--mount',f'type=bind,source={ROOT / "web"},target=/web',
        '--mount','type=volume,source=aheadlab-stocksense-browser-node,target=/seed,readonly',
        '--mount','type=volume,source=aheadlab-carbon-node,target=/web/node_modules',
        '-w','/web','node:22-bookworm-slim','sh','-c','cp -a /seed/. /web/node_modules/ && npm run build'])
elif phase=='build':run(compose+['build'])
elif phase=='up':run(compose+['up','-d','--no-deps','--wait','--wait-timeout','120','carbonshift'])
elif phase=='stop':run(compose+['stop','carbonshift'])
elif phase=='browser':
    run(['docker','run','--rm','--network','carbonshift_default','--memory','1g','--memory-swap','1g','--cpus','1','--shm-size','256m',
        '--mount',f'type=bind,source={ROOT / "web"},target=/web',
        '--mount','type=volume,source=aheadlab-carbon-node,target=/web/node_modules',
        '-e','BASE_URL=http://carbonshift:8501','-w','/web','mcr.microsoft.com/playwright:v1.56.1-noble','npx','playwright','test'])
else:raise ValueError(phase)
