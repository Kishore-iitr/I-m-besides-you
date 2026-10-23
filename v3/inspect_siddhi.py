import json, sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

base = Path(r'G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_a')
sdir = base / 'ses_20260701-043922-SIDDHIGUPTAB00B'
print('Session exists:', sdir.exists())

with open(sdir / 'gt_manifest.json', 'r', encoding='utf-8') as f:
    gt = json.load(f)

print('Processes in GT:', len(gt['processes']))
total_execs = 0
for p in gt['processes']:
    execs = p.get('executions', [])
    total_execs += len(execs)
    print(f"  {p['code']} ({p['family_name']}): {len(execs)} execs")

print('Total GT executions:', total_execs)
