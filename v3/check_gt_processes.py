import json, sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

base = Path(r'G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_a\ses_20260701-043922-SIDDHIGUPTAB00B')
with open(base / 'gt.jsonl', 'r', encoding='utf-8') as f:
    procs = []
    for line in f:
        d = json.loads(line)
        if d.get('event') == 'process_started':
            procs.append(d)

print(f"Total process_started in gt.jsonl: {len(procs)}")
for i, p in enumerate(procs):
    print(f"  {i+1:02d}. {p.get('ts_utc')} | Code: {p.get('process_code')} | Name: {p.get('process_name')} | Case: {p.get('case_id')}")
