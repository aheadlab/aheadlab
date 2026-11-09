"""Inspect the published Khepri source; download bounded public artifacts only."""
import hashlib,json,sys,urllib.request
from pathlib import Path
OUT=Path(__file__).resolve().parent/'carbon_source'
OUT.mkdir(exist_ok=True)
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Aheadlab-research'}),timeout=60) as response:
        return response.read()
if not (OUT/'tree.json').exists():
    tree=json.loads(get('https://api.github.com/repos/avalyset/khepri-tsfm/git/trees/v1.0.1?recursive=1'))
    (OUT/'tree.json').write_text(json.dumps(tree,indent=2))
tree=json.loads((OUT/'tree.json').read_text())
print('Commit',tree['sha'])
items=[x for x in tree['tree'] if x['type']=='blob' and (x['path'].startswith(('data/CI_','predictions/PRED-')) or x['path'] in ['LICENSE-DATA','README.md','khepri_tsfm/data.py','khepri_tsfm/models.py','repro_from_ci.py']) and not any(n in x['path'] for n in ['Chronos-2','Timestral-209M'])]
for item in items:print(item['path'],item.get('size',0))
if '--download' in sys.argv:
    manifest=[]
    for item in items:
        if item.get('size',0)>100*1024**2:raise ValueError('Artifact over 100 MiB')
        path=OUT/item['path'];path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():path.write_bytes(get('https://raw.githubusercontent.com/avalyset/khepri-tsfm/'+tree['sha']+'/'+item['path']))
        blob=path.read_bytes()
        assert hashlib.sha1(b'blob '+str(len(blob)).encode()+b'\0'+blob).hexdigest()==item['sha']
        manifest.append(dict(path=item['path'],bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest()))
    (OUT/'download_manifest.json').write_text(json.dumps(dict(commit=tree['sha'],files=manifest),indent=2))
