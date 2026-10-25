import json, sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

base = Path(r'G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_a\ses_20260701-043922-SIDDHIGUPTAB00B')
with open(base / 'gt_manifest.json', 'r', encoding='utf-8') as f:
    gt = json.load(f)

gt_execs = []
for p in gt['processes']:
    for e in p['executions']:
        gt_execs.append({
            'code': p['code'],
            'family': p['family_name'],
            'case_id': e['case_id'],
            'start_ts': e['start_ts'],
            'end_ts': e['end_ts']
        })

gt_execs.sort(key=lambda x: x['start_ts'])
print('First 10 GT executions:')
for i, e in enumerate(gt_execs[:10], 1):
    print(f"  {i:02d}. Case: {e['case_id']:<18} | {e['start_ts']} -> {e['end_ts']} | Code: {e['code']}")

print('\nCheck for overlaps in GT itself:')
for i in range(len(gt_execs) - 1):
    cur_end = gt_execs[i]['end_ts']
    next_start = gt_execs[i+1]['start_ts']
    if cur_end > next_start:
        print(f"  OVERLAP in GT! Case {gt_execs[i]['case_id']} ends at {cur_end}, but next case {gt_execs[i+1]['case_id']} starts at {next_start}!")
    elif cur_end == next_start:
        pass
    else:
        print(f"  GAP in GT between {gt_execs[i]['case_id']} ({cur_end}) and {gt_execs[i+1]['case_id']} ({next_start})")
