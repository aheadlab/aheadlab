"""Run a read-only, bounded exploratory job without touching running services."""
import argparse,ctypes,json,subprocess,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'validation/case_search'
def ram():
    class M(ctypes.Structure):
        _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in ['total','available','pt','pa','vt','va','ex']]
    m=M();m.length=ctypes.sizeof(m)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):raise RuntimeError('RAM unavailable')
    return m.available/1024**3
def services():
    ids=subprocess.check_output(['docker','ps','-q'],text=True).split()
    data=json.loads(subprocess.check_output(['docker','inspect',*ids],text=True)) if ids else []
    return {r['Name']:[r['Id'],r['State']['StartedAt'],r['RestartCount']] for r in data}
parser=argparse.ArgumentParser();parser.add_argument('phase',nargs='?',default='explore_windows',choices=['explore_windows','explore_carbon'])
phase=parser.parse_args().phase
before=services();minimum=ram();assert minimum>=5
name='aheadlab-case-search-'+uuid.uuid4().hex[:8]
command=['docker','run','--rm','--name',name,'--no-healthcheck','--network','none','--cpus','1','--memory','2g','--memory-swap','2g',
    '--mount',f'type=bind,source={ROOT},target=/workspace,readonly','--mount',f'type=bind,source={OUT},target=/out',
    '-e','OPENBLAS_NUM_THREADS=1','-e','PYTHONDONTWRITEBYTECODE=1','aheadlab-capacity-validation',
    'python',f'/workspace/validation/case_search/{phase}.py']
with (OUT/f'{phase}.log').open('w') as log:
    job=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
    try:
        while job.poll() is None:
            minimum=min(minimum,ram())
            if minimum<4:raise RuntimeError('Host RAM reserve below 4 GiB')
            time.sleep(2)
    except BaseException:
        subprocess.run(['docker','stop','--time','5',name],check=False);job.wait();raise
after=services();assert after==before
(OUT/f'{phase}_resources.json').write_text(json.dumps(dict(min_host_available_gib=minimum,services_unchanged=len(before),memory_limit_gib=2,cpu=1,exit_code=job.returncode),indent=2))
print((OUT/f'{phase}.log').read_text())
if job.returncode:raise SystemExit(job.returncode)
