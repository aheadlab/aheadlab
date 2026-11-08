"""Stream only the official hourly institution file, with the author's digest."""
import hashlib
import json
from pathlib import Path
import shutil
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT=Path(__file__).resolve().parents[1]
NAME='CESNET-TimeSeries26-institutions-1_hour.h5'
SHA256='57430eb3ea714cbeceb9b4c026010aa158b79432b7e1af291fc1cf1eebd7d49e'
BASE='https://zenodo.org/api/records/23283552/files/'
AUTHOR='https://raw.githubusercontent.com/CESNET/cesnet-tszoo/main/cesnet_tszoo/datasets/databases/cesnet_timeseries26/constants.py'


def checksum(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def main():
    raw=ROOT/'data/raw';raw.mkdir(parents=True,exist_ok=True)
    target=raw/'institutions26-hour.h5'
    urls=[BASE+NAME+f'.{i:03d}/content' for i in [1,2]]
    if not target.exists():
        parts=[]
        for i,url in enumerate(urls,1):
            part=raw/f'institutions26-hour.part{i}'
            if not part.exists():
                for attempt in range(3):
                    try:
                        request=urllib.request.Request(url,headers={'User-Agent':'Aheadlab-research/0.2'})
                        with urllib.request.urlopen(request,timeout=120) as response,part.with_suffix('.download').open('wb') as output:
                            total=0;length=response.headers.get('Content-Length')
                            while block:=response.read(1024*1024):
                                total+=len(block)
                                if total>510_000_000:raise ValueError('Part larger than official 500 MB split')
                                output.write(block)
                                if total%(50*1024**2)==0:print(f'Part {i}: {total//1024**2} MiB',flush=True)
                            if length is not None and total!=int(length):raise ValueError('Truncated download')
                        part.with_suffix('.download').replace(part)
                        break
                    except Exception:
                        if attempt==2:raise
                        time.sleep(2)
            parts.append(part)
        combined=target.with_suffix('.assembled')
        with combined.open('wb') as output:
            for part in parts:
                with part.open('rb') as stream:shutil.copyfileobj(stream,output,1024*1024)
        if checksum(combined)!=SHA256:raise ValueError('Official checksum mismatch')
        combined.replace(target)
    if checksum(target)!=SHA256:raise ValueError('Existing file checksum mismatch')
    metadata=dict(dataset='CESNET-TimeSeries26',urls=urls,sha256=SHA256,bytes=target.stat().st_size,
        checksum_source=AUTHOR,record='https://zenodo.org/records/23283552',
        citation='https://doi.org/10.5281/zenodo.21945629',license='CC-BY-4.0')
    (ROOT/'data/source26.json').write_text(json.dumps(metadata,indent=2))
    print('Verified',target.name,target.stat().st_size,flush=True)


def parallel_main():
    """Four bounded range requests; validate each range and the complete file."""
    url='https://drive.usercontent.google.com/download?id=18zB39Ya_i1z7ZJehD9LLiXPIyyotneri&export=download&confirm=t'
    total=531400262;chunk_size=8*1024**2
    raw=ROOT/'data/raw';raw.mkdir(parents=True,exist_ok=True)
    target=raw/'institutions26-hour.h5';parts=raw/'institutions26-chunks';parts.mkdir(exist_ok=True)
    def fetch(start):
        stop=min(start+chunk_size,total)-1;file=parts/f'{start:012d}.part'
        if file.exists() and file.stat().st_size==stop-start+1:return file
        for attempt in range(3):
            try:
                request=urllib.request.Request(url,headers={'Range':f'bytes={start}-{stop}','User-Agent':'Aheadlab-research/0.2'})
                with urllib.request.urlopen(request,timeout=90) as response,file.with_suffix('.tmp').open('wb') as output:
                    if response.status!=206 or response.headers.get('Content-Range')!=f'bytes {start}-{stop}/{total}':
                        raise ValueError('Mirror did not honor the requested range')
                    size=0
                    while block:=response.read(1024*1024):
                        size+=len(block)
                        if size>stop-start+1:raise ValueError('Unexpected range size')
                        output.write(block)
                if size!=stop-start+1:raise ValueError('Truncated range')
                file.with_suffix('.tmp').replace(file);return file
            except Exception:
                if attempt==2:raise
                time.sleep(2)
    if not target.exists():
        starts=list(range(0,total,chunk_size));completed=0
        with ThreadPoolExecutor(max_workers=4) as executor:
            tasks=[executor.submit(fetch,start) for start in starts]
            for task in as_completed(tasks):
                completed+=task.result().stat().st_size
                print(f'Official mirror: {completed//1024**2}/{total//1024**2} MiB',flush=True)
        combined=target.with_suffix('.assembled')
        with combined.open('wb') as output:
            for start in starts:
                with (parts/f'{start:012d}.part').open('rb') as stream:shutil.copyfileobj(stream,output,1024*1024)
        if checksum(combined)!=SHA256:raise ValueError('Official whole-file checksum mismatch')
        combined.replace(target)
    if checksum(target)!=SHA256:raise ValueError('Existing file checksum mismatch')
    (ROOT/'data/source26.json').write_text(json.dumps(dict(dataset='CESNET-TimeSeries26',url=url,
        sha256=SHA256,bytes=target.stat().st_size,checksum_source=AUTHOR,
        record='https://zenodo.org/records/23283552',citation='https://doi.org/10.5281/zenodo.21945629',
        license='CC-BY-4.0',download='4 parallel byte ranges, 1 MiB streaming buffers'),indent=2))
    print('Verified',target.name,target.stat().st_size,flush=True)


if __name__=='__main__':main()
