import json, sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
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

print('Total events:', len(events))
# Find events with ORD-100848-001
ord_events = [e for e in events if 'ORD-100848-001' in (str(e.get('context')) + str(e.get('payload')))]
print(f'Events with ORD-100848-001: {len(ord_events)}')
print(f"First event: {ord_events[0]['timestamp_iso']} | event_type: {ord_events[0].get('event_type')}")
print(f"Last event:  {ord_events[-1]['timestamp_iso']} | event_type: {ord_events[-1].get('event_type')}")

# Compare with GT for ORD-100848-001:
# GT: 2026-07-01T04:40:14.127234+00:00 -> 2026-07-01T04:40:49.037451+00:00
print('\nGround Truth:')
print('GT Start: 2026-07-01T04:40:14.127234+00:00')
print('GT End:   2026-07-01T04:40:49.037451+00:00')

# What events happened right at 04:40:14.127?
print('\nEvents near GT Start (04:40:14):')
for e in events:
    ts = e.get('timestamp_iso', '')
    if '04:40:1' in ts:
        ctx = e.get('context') or {}
        act = ctx.get('active_app') or {}
        pld = str(e.get('payload') or '')[:50]
        ext = str(ctx.get('extracted_text') or '')[:50]
        print(f"  {ts} | {e.get('event_type')} | {act.get('app_name')} | {act.get('window_title')[:30]} | {pld}")
        if '04:40:16' in ts:
            break

# What events happened right at GT End (04:40:49)?
print('\nEvents near GT End (04:40:49):')
for e in events:
    ts = e.get('timestamp_iso', '')
    if '04:40:48' in ts or '04:40:49' in ts or '04:40:50' in ts:
        ctx = e.get('context') or {}
        act = ctx.get('active_app') or {}
        pld = str(e.get('payload') or '')[:50]
        print(f"  {ts} | {e.get('event_type')} | {act.get('app_name')} | {act.get('window_title')[:30]} | {pld}")
