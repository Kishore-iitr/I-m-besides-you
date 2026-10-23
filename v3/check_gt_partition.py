import json
from pathlib import Path
from datetime import datetime

def to_epoch(ts):
    if not ts: return 0.0
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.timestamp()
    except Exception:
        return 0.0

base = Path(r'G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_a\ses_20260701-043922-SIDDHIGUPTAB00B')
with open(base / 'gt_manifest.json', 'r', encoding='utf-8') as f:
    gt = json.load(f)

gt_execs = []
for p in gt['processes']:
    for e in p['executions']:
        gt_execs.append({
            'code': p['code'],
            'case_id': e.get('case_id'),
            'start_ts': e['start_ts'],
            'end_ts': e['end_ts'],
            'start_sec': to_epoch(e['start_ts']),
            'end_sec': to_epoch(e['end_ts'])
        })

gt_execs.sort(key=lambda x: x['start_sec'])

print(f"Total GT Executions: {len(gt_execs)}")
for i in range(len(gt_execs)):
    e = gt_execs[i]
    next_start = gt_execs[i+1]['start_sec'] if i + 1 < len(gt_execs) else None
    gap = (next_start - e['end_sec']) if (next_start and e['end_sec'] > 0) else None
    print(f"{i+1:02d}. Case: {str(e['case_id']):<18} | Start: {e['start_ts'][:19]} | End: {str(e['end_ts'])[:19]} | Gap to Next: {f'{gap:.3f}s' if gap is not None else 'N/A'}")
