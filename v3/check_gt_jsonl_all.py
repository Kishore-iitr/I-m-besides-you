import json, sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

base = Path(r'G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_a\ses_20260701-043922-SIDDHIGUPTAB00B')
with open(base / 'gt.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        d = json.loads(line)
        ev = d.get('event')
        if ev in ('process_started', 'task_started'):
            ts = d.get('ts_utc')[:19]
            proc = d.get('current_process')
            pname = d.get('process_name', '')
            cid = d.get('case_id') or d.get('task_id')
            action = d.get('action', '')
            entity = d.get('entity', '')
            print(f"{ts} | {ev:<15} | {proc} ({pname}) | {cid} | act: {action} | ent: {entity}")
