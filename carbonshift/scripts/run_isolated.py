"""Windows research runner: one bounded offline job, existing services unchanged."""
import argparse,ctypes,json,subprocess,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent;OUT=ROOT/'results'
def ram():
    class M(ctypes.Structure):
        _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in ['total','available','pt','pa','vt','va','ex']]
    m=M();m.length=ctypes.sizeof(m)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):raise RuntimeError('RAM unavailable')
    return m.available/1024**3
def services():
    ids=subprocess.check_output(['docker','ps','-q'],text=True).split()
    records=json.loads(subprocess.check_output(['docker','inspect',*ids],text=True)) if ids else []
    return {r['Name']:dict(id=r['Id'],started=r['State']['StartedAt'],restarts=r['RestartCount']) for r in records}
def main():
    parser=argparse.ArgumentParser();parser.add_argument('phases',nargs='+',choices=['benchmark','reproduce','test','report'])
    phases=parser.parse_args().phases;OUT.mkdir(exist_ok=True);(ROOT/'data').mkdir(exist_ok=True)
    before=services();minimum=ram();assert minimum>=5
    run_id=uuid.uuid4().hex[:8]
    try:
        for phase in phases:
            if ram()<5:raise RuntimeError('Host reserve below 5 GiB')
            name=f'aheadlab-carbon-check-{run_id}-{phase}'
            command=['docker','run','--rm','--name',name,'--no-healthcheck','--network','none','--cpus','1','--memory','2g','--memory-swap','2g','--pids-limit','256',
                '--mount',f'type=bind,source={ROOT},target=/project,readonly','--mount',f'type=bind,source={OUT},target=/project/results',
                '--mount',f'type=bind,source={ROOT / "data"},target=/project/data',
                '--mount','type=volume,source=aheadlab-hf,target=/home/app/.cache/huggingface,readonly',
                '-e','HF_HUB_OFFLINE=1','-e','OMP_NUM_THREADS=1','-e','MKL_NUM_THREADS=1','-e','OPENBLAS_NUM_THREADS=1',
                '-e','NUMBA_NUM_THREADS=1','-e','NUMBA_CACHE_DIR=/tmp/numba','-e','PYTHONDONTWRITEBYTECODE=1','-e','PYTHONPATH=/project/src',
                '-w','/project','aheadlab-capacity-validation']
            command+=['pytest','-q','-p','no:cacheprovider','--basetemp=/tmp/tests'] if phase=='test' else ['python',f'scripts/{phase}.py']
            print('Start',phase,'host free',round(ram(),2),'GiB',flush=True)
            with (OUT/f'{phase}.log').open('w') as log:
                job=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
                try:
                    while job.poll() is None:
                        minimum=min(minimum,ram())
                        if minimum<4:raise RuntimeError('Host reserve below 4 GiB')
                        time.sleep(3)
                except BaseException:
                    subprocess.run(['docker','stop','--time','5',name],check=False);job.wait();raise
            print((OUT/f'{phase}.log').read_text()[-7000:],flush=True)
            if job.returncode:raise RuntimeError(f'{phase} failed')
    finally:
        after=services();unchanged=after==before
        (OUT/f'run_{run_id}.json').write_text(json.dumps(dict(phases=phases,services_unchanged=unchanged,
            existing_services=len(before),min_host_available_gib=minimum,memory_limit_gib=2,cpu=1,network='none'),indent=2))
        if not unchanged:raise RuntimeError('Existing services changed')
        print('Existing services unchanged',len(before),flush=True)
if __name__=='__main__':main()
