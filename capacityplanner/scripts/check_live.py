"""Read-only checks of the local fourth app and the pre-existing services."""
import json
from pathlib import Path
import subprocess
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/cesnet'


def main():
    checks={}
    for size in ['5M','28M']:
        request=urllib.request.Request('http://127.0.0.1:8504/api/forecast',
            data=json.dumps(dict(source='synthetic',model=size)).encode(),
            headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=90) as response:
            data=json.load(response)
        assert data['model']==size and len(data['forecast'])==24
        assert all(r['lower']<=r['median']<=r['upper'] for r in data['forecast'])
        checks[size]=dict(status='passed',hours=24,unit_hours=data['metrics']['unit_hours'])
    snapshots=sorted(OUT.glob('services_before_*.json'),key=lambda p:p.stat().st_mtime)
    if not snapshots:
        raise RuntimeError('Run an isolated check first to record the existing services')
    before=json.loads(snapshots[0].read_text())
    records=json.loads(subprocess.check_output(['docker','inspect',*[v['id'] for v in before.values()]],text=True))
    after={r['Name']:dict(id=r['Id'],started=r['State']['StartedAt'],restarts=r['RestartCount'],
        running=r['State']['Running'],health=r['State'].get('Health',{}).get('Status')) for r in records}
    assert before==after, 'An existing service changed'
    current=json.loads(subprocess.check_output(['docker','inspect','capacityplanner-capacityplanner-1'],text=True))[0]
    assert current['State']['Health']['Status']=='healthy'
    assert current['HostConfig']['Memory']==2*1024**3 and current['HostConfig']['NanoCpus']==10**9
    result=dict(real_model_http=checks,existing_services=len(before),existing_services_unchanged=True,
        new_app_health='healthy',limits=dict(memory_gib=2,cpu=1),url='http://localhost:8504')
    (OUT/'live_verification.json').write_text(json.dumps(result,indent=2))
    code="import importlib.metadata as m,json; print(json.dumps({n:m.version(n) for n in ['numpy','pandas','statsforecast','torch','timestral','fastapi','pyarrow']},indent=2))"
    versions=subprocess.check_output(['docker','exec','capacityplanner-capacityplanner-1','python','-c',code],text=True)
    (OUT/'runtime_versions.json').write_text(versions)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
