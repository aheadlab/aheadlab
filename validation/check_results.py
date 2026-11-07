"""Check experiment completeness and inventory conservation from saved artifacts."""
import csv
import json
from pathlib import Path

OUT = Path(__file__).parent/'results'


def rows(name):
    with (OUT/f'{name}.csv').open(newline='') as f:
        return list(csv.DictReader(f))


metadata = json.loads((OUT/'stock_metadata.json').read_text())
assert metadata['reproduced_pairs'] == 400
assert metadata['max_mae_difference'] < .001, metadata
scores = rows('stock_new_scores')
assert len(scores) == 50*8*4
assert len({(r['sku'],r['fold'],r['model']) for r in scores}) == len(scores)
assert all(float(r['mae']) >= 0 for r in scores)
ledger = rows('stock_equal_policy_ledger')
assert len(ledger) == 50*180*4*3
actual = {}
states = {}
for r in ledger:
    demand, lost, inventory = (float(r[k]) for k in ['demand','lost','inventory'])
    assert demand >= lost >= 0 and inventory >= 0
    key = (r['sku'],r['date'])
    assert key not in actual or actual[key] == demand
    actual[key] = demand
    key = (r['sku'],r['model'],r['level'])
    if key not in states:
        states[key] = dict(previous=None, orders=[])
    state = states[key]
    if state['previous'] is not None:
        arrived = state['orders'][-14] if len(state['orders']) >= 14 else 0
        assert abs(inventory-(state['previous']+arrived-(demand-lost))) < 1e-7
    state['previous'] = inventory
    state['orders'].append(float(r['order']))
summary = rows('stock_equal_policy_summary')
assert len(summary) == 12
assert max(float(r['demand']) for r in summary) == min(float(r['demand']) for r in summary)
assert len(rows('solar_matched_regression')) == 4*728
assert len(rows('cloud_extended_anomalies')) == 6
assert len(rows('cloud_extended_delays')) == 36
print('PASS: complete paired scores, original 5M reproduced, common demand, inventory conservation, solar and cloud outputs')
