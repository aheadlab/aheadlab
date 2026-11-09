"""Read-only HTTP checks plus one explicit local 5M inference."""
import json,math,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE='http://127.0.0.1:8505'
def call(path,payload=None):
    data=None if payload is None else json.dumps(payload).encode()
    request=urllib.request.Request(BASE+path,data=data,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=90) as response:return json.load(response)
def main():
    assert call('/api/health')['app']=='carbonshift'
    meta=call('/api/meta');assert len(meta['cases'])==54
    case=json.loads((ROOT/'results/replays.json').read_text())[0]
    params=dict(case_id=case['id'],comparator='GBM',duration=4,deadline=96,energy_kwh=1000)
    plan=call('/api/plan',params);assert len(plan['times'])==96
    result=call('/api/forecast',dict(history=case['history'],duration=4,deadline=96,energy_kwh=1000))
    assert len(result['forecast'])==96 and all(math.isfinite(v) and v>=0 for v in result['forecast'])
    assert result['plan']['stop']-result['plan']['start']==4 and result['plan']['stop']<=96
    record=dict(health=True,replay_api=True,real_timestral_5m_inference=True,history_hours=len(case['history']),
        forecast_hours=96,window_start=result['plan']['start'],window_stop=result['plan']['stop'])
    (ROOT/'results/live_validation.json').write_text(json.dumps(record,indent=2))
    print(json.dumps(record,indent=2))
if __name__=='__main__':main()
