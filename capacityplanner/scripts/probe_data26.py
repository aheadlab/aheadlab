"""Check official mirror responses before choosing a faster bounded download."""
import time
import urllib.request

urls=[
 'https://zenodo.org/api/records/23283552/files/CESNET-TimeSeries26-institutions-1_hour.h5.001/content',
 'https://drive.usercontent.google.com/download?id=18zB39Ya_i1z7ZJehD9LLiXPIyyotneri&export=download&confirm=t',
]
for url in urls:
    begun=time.time()
    try:
        request=urllib.request.Request(url,headers={'Range':'bytes=0-1023','User-Agent':'Aheadlab-research/0.2'})
        with urllib.request.urlopen(request,timeout=30) as response:
            data=response.read(1024)
            print(dict(host=url.split('/')[2],status=response.status,content_type=response.headers.get('Content-Type'),
                length=response.headers.get('Content-Length'),range=response.headers.get('Content-Range'),
                signature=data[:8].hex(),seconds=round(time.time()-begun,2)),flush=True)
    except Exception as error:print(type(error).__name__,str(error),flush=True)
