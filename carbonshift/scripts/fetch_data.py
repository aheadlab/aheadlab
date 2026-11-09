"""Explicit streaming download of pinned, attributed Khepri source artifacts."""
import hashlib,json,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];RAW=ROOT/'data/raw'
def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024**2),b''):digest.update(chunk)
    return digest.hexdigest()
def main():
    manifest=json.loads((ROOT/'data/source.json').read_text());RAW.mkdir(parents=True,exist_ok=True)
    for record in manifest['files']:
        path=RAW/record['path']
        if not path.resolve().is_relative_to(RAW.resolve()):raise ValueError('Invalid source path')
        if record['bytes']>100*1024**2:raise ValueError('Artifact exceeds download bound')
        if not path.exists():
            path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_suffix(path.suffix+'.download')
            url='https://raw.githubusercontent.com/avalyset/khepri-tsfm/'+manifest['commit']+'/'+record['path']
            req=urllib.request.Request(url,headers={'User-Agent':'Aheadlab-CarbonShift-research'})
            size=0
            with urllib.request.urlopen(req,timeout=90) as response,temporary.open('wb') as output:
                while chunk:=response.read(1024**2):
                    size+=len(chunk)
                    if size>record['bytes']:raise ValueError('Unexpected artifact size')
                    output.write(chunk)
            if size!=record['bytes'] or sha(temporary)!=record['sha256']:raise ValueError('Source checksum mismatch')
            temporary.replace(path)
        if sha(path)!=record['sha256']:raise ValueError('Existing source checksum mismatch')
        print('Verified',record['path'],flush=True)
    (RAW/'download_manifest.json').write_text(json.dumps(manifest,indent=2))
if __name__=='__main__':main()
