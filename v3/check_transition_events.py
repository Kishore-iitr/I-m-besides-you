import json
from pathlib import Path

base = Path(r'G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_a\ses_20260701-043922-SIDDHIGUPTAB00B')
chunk_dirs = sorted([p for p in base.iterdir() if p.is_dir() and 'chunk' in p.name and (p / 'events.jsonl').exists()])

events = []
for c in chunk_dirs:
    with open(c / 'events.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
events.sort(key=lambda x: x.get('timestamp_ms', 0))

print('Events between 04:40:30 and 04:40:55:')
for e in events:
    ts = e.get('timestamp_iso', '')
    if '04:40:3' in ts or '04:40:4' in ts or '04:40:5' in ts:
        ctx = e.get('context') or {}
        act = ctx.get('active_app') or {}
        txt = str(ctx.get('extracted_text') or '')
        cid = ''
        if 'ORD-100848-001' in (str(e.get('context')) + str(e.get('payload'))):
            cid = '[ORD-100848-001]'
        elif 'STK-100848-001' in (str(e.get('context')) + str(e.get('payload'))):
            cid = '[STK-100848-001]'
        pld = str(e.get('payload') or '')[:40]
        print(f"  {ts} | {e.get('event_type'):<18} | {act.get('app_name'):<15} | {cid:<16} | {pld}")
