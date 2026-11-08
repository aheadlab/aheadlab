"""Explicit bounded streaming download of the official CC-BY-4.0 CESNET source."""
import sys
if '--ts26' in sys.argv:
    from fetch_data26 import parallel_main
    parallel_main()
    sys.exit(0)

import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://zenodo.org/api/records/23296272/files/CESNET-TimeSeries24-institutions-hour.h5/content'
SHA256 = '1b9ecc4b08e768fa7374d064d96e3fd626640487f1973e2d248f7d02cb91a838'
TARGET = ROOT/'data/raw/institutions-hour.h5'
TARGET.parent.mkdir(parents=True,exist_ok=True)


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


if not TARGET.exists():
    temp=TARGET.with_suffix('.part')
    request=urllib.request.Request(URL,headers={'User-Agent':'Aheadlab-research/0.1'})
    with urllib.request.urlopen(request,timeout=120) as response,temp.open('wb') as out:
        total=0
        while chunk:=response.read(1024*1024):
            total+=len(chunk)
            if total>200_000_000:raise ValueError('Unexpected archive size')
            out.write(chunk)
            if total%(20*1024*1024)==0:print(f'{total//1024//1024} MiB',flush=True)
    assert digest(temp)==SHA256,'Checksum mismatch; original file not installed'
    temp.replace(TARGET)
assert digest(TARGET)==SHA256,'Existing source checksum mismatch'
(ROOT/'data/source.json').write_text(json.dumps(dict(url=URL,sha256=SHA256,
    bytes=TARGET.stat().st_size,license='CC-BY-4.0',
    citation='CESNET-TimeSeries24, https://doi.org/10.1038/s41597-025-04603-x',
    distribution='CESNET TS-Zoo HDF5 distribution, Zenodo record 23296272'),indent=2))
print('Verified',TARGET.name,TARGET.stat().st_size,flush=True)
