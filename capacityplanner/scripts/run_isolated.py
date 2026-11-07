"""Host runner: one capped disposable container; never manage existing services."""
import argparse
import ctypes
import json
from pathlib import Path
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'capacityplanner/results/cesnet'


def free_ram():
    class Memory(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [
            (n, ctypes.c_ulonglong) for n in ['total','available','page_total','page_available',
                                            'virtual_total','virtual_available','extended']]
    memory = Memory()
    memory.length = ctypes.sizeof(memory)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
        raise RuntimeError('Cannot inspect host memory')
    return memory.available


def services():
    ids = subprocess.check_output(['docker','ps','-q'], text=True).split()
    records = json.loads(subprocess.check_output(['docker','inspect',*ids], text=True)) if ids else []
    return {r['Name']: dict(id=r['Id'], started=r['State']['StartedAt'],
        restarts=r['RestartCount'], running=r['State']['Running'],
        health=r['State'].get('Health',{}).get('Status')) for r in records}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phases', nargs='+')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    before = services()
    (OUT/f'services_before_{run_id}.json').write_text(json.dumps(before, indent=2))
    monitoring = []
    try:
        for phase in args.phases:
            if phase not in ['inspect','prepare','benchmark','test','analyze','environment']:
                raise ValueError(phase)
            if free_ram() < 5*1024**3:
                raise RuntimeError('Less than 5 GiB host RAM free; job not started')
            project = 'capacityplanner'
            name = f'aheadlab-capacity-check-{run_id}-{phase}'
            command = ['docker','run','--rm','--name',name,'--network','none','--cpus','1',
                '--memory','2g','--memory-swap','2g','--pids-limit','256',
                '--mount',f'type=bind,source={ROOT},target=/workspace,readonly',
                '--mount',f'type=bind,source={OUT},target=/out',
                '--mount',f'type=bind,source={ROOT / project / "data"},target=/workspace/{project}/data',
                '--mount','type=volume,source=aheadlab-hf,target=/home/app/.cache/huggingface,readonly',
                '-e','HF_HUB_OFFLINE=1','-e','OMP_NUM_THREADS=1','-e','MKL_NUM_THREADS=1',
                '-e','OPENBLAS_NUM_THREADS=1','-e','NUMBA_NUM_THREADS=1','-e','NUMBA_CACHE_DIR=/tmp/numba',
                '-e','PYTHONDONTWRITEBYTECODE=1','-e','RUN_MODEL_TESTS=0',
                '-e',f'PYTHONPATH=/workspace/{project}/src',
                '-w',f'/workspace/{project}','aheadlab-capacity-validation']
            if phase == 'test':
                command += ['pytest','-q','-p','no:cacheprovider','--basetemp=/tmp/tests']
            else:
                command += ['python',f'/workspace/{project}/scripts/research.py',phase]
            print(f'Start {phase}; host free {free_ram()/1024**3:.2f} GiB', flush=True)
            (OUT/f'{phase}.command.json').write_text(json.dumps(command, indent=2))
            with (OUT/f'{phase}.log').open('w') as log:
                job = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
                try:
                    while job.poll() is None:
                        available = free_ram()
                        monitoring.append(dict(time=time.time(), phase=phase, host_available_gib=available/1024**3))
                        if available < 4*1024**3:
                            raise RuntimeError('Host reserve below 4 GiB')
                        time.sleep(5)
                except BaseException:
                    subprocess.run(['docker','stop','--time','5',name], check=False)
                    job.wait()
                    raise
            print(f'{phase}: exit {job.returncode}', flush=True)
            if job.returncode:
                print((OUT/f'{phase}.log').read_text()[-4000:], flush=True)
                raise RuntimeError(f'Failed: {phase}')
    finally:
        after = services()
        (OUT/f'services_after_{run_id}.json').write_text(json.dumps(after, indent=2))
        (OUT/f'memory_{run_id}.json').write_text(json.dumps(monitoring, indent=2))
        unchanged = all(after.get(k) == v for k,v in before.items())
        (OUT/f'run_{run_id}.json').write_text(json.dumps(dict(phases=args.phases,
            services_unchanged=unchanged, existing_services=len(before),
            min_host_available_gib=min((r['host_available_gib'] for r in monitoring), default=None),
            limits=dict(memory_gib=2, cpu=1, network='none', extra_swap=0)), indent=2))
        print(f'Existing services unchanged: {unchanged}', flush=True)
        if not unchanged:
            raise RuntimeError('Existing service state changed; inspect snapshots')


if __name__ == '__main__':
    main()
