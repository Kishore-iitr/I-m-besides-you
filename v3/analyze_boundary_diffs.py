import json, re, sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
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

gt_map = {}
for p in gt['processes']:
    for e in p['executions']:
        cid = e.get('case_id')
        if cid:
            gt_map[cid] = {
                'code': p['code'],
                'family': p['family_name'],
                'start_ts': e['start_ts'],
                'end_ts': e['end_ts'],
                'start_sec': to_epoch(e['start_ts']),
                'end_sec': to_epoch(e['end_ts'])
            }

chunk_dirs = sorted([p for p in base.iterdir() if p.is_dir() and 'chunk' in p.name and (p / 'events.jsonl').exists()])
events = []
for c in chunk_dirs:
    with open(c / 'events.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
events.sort(key=lambda x: x.get('timestamp_ms', 0))

dom = '100848'
case_first = {}
case_last = {}
for i, ev in enumerate(events):
    ctx = ev.get('context') or {}
    act = ctx.get('active_app') or {}
    text = ' '.join([act.get('window_title') or '', str(ctx.get('extracted_text') or ''), str(ev.get('payload') or '')])
    for m in re.finditer(rf'\b([A-Z]{{2,6}})-{dom}-(\d{{3}})\b', text):
        cid = f'{m.group(1)}-{dom}-{m.group(2)}'
        if cid not in case_first:
            case_first[cid] = i
        case_last[cid] = i

ordered_cases = sorted(case_first.keys(), key=lambda c: case_first[c])

print(f"{'Case ID':<18} | {'GT Start':<24} {'First Event':<24} {'Diff Start':>10} | {'GT End':<24} {'Last Event':<24} {'Diff End':>10}")
print("-" * 125)
diff_starts = []
diff_ends = []
for cid in ordered_cases[:15]:
    if cid in gt_map:
        gt = gt_map[cid]
        fev = events[case_first[cid]]
        lev = events[case_last[cid]]
        fev_sec = to_epoch(fev['timestamp_iso'])
        lev_sec = to_epoch(lev['timestamp_iso'])
        
        d_start = fev_sec - gt['start_sec']
        d_end = lev_sec - gt['end_sec'] if gt['end_sec'] > 0 else 0
        diff_starts.append(d_start)
        if gt['end_sec'] > 0:
            diff_ends.append(d_end)
            
        print(f"{cid:<18} | {gt['start_ts'][:23]:<24} {fev['timestamp_iso'][:23]:<24} {d_start:>9.2f}s | {str(gt['end_ts'])[:23]:<24} {lev['timestamp_iso'][:23]:<24} {d_end:>9.2f}s")
