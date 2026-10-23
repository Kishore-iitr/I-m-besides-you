import json, sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

base = Path(r'G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_a\ses_20260701-043922-SIDDHIGUPTAB00B')
chunk_dirs = sorted([p for p in base.iterdir() if p.is_dir() and 'chunk_' in p.name and (p / 'events.jsonl').exists()])

events = []
for c in chunk_dirs:
    with open(c / 'events.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
events.sort(key=lambda x: x.get('timestamp_ms', 0))

print('Events between 04:53:35 and 04:54:25:')
for e in events:
    ts = e.get('timestamp_iso', '')
    if '04:53:3' in ts or '04:53:4' in ts or '04:53:5' in ts or '04:54:0' in ts or '04:54:1' in ts or '04:54:2' in ts:
        ctx = e.get('context') or {}
        act = ctx.get('active_app') or {}
        txt = str(ctx.get('extracted_text') or '')
        pld = str(e.get('payload') or '')
        ev_type = e.get('event_type')
        print(f"  {ts} | {ev_type:<18} | {act.get('app_name')} | {act.get('window_title')[:30]} | pld: {pld[:60]} | txt: {txt[:60]}")
