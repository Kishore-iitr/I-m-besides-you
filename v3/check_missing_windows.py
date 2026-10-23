import json
from pathlib import Path

base = Path(r'G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_a\ses_20260701-043922-SIDDHIGUPTAB00B')
with open(base / 'gt_manifest.json', 'r', encoding='utf-8') as f:
    gt = json.load(f)

# Collect missing executions
missing_cids = [
    'ORD-100848-002', 'ORD-100848-003', 'ORD-100848-004', 'ORD-100848-005',
    'SHP-100848-001', 'SHP-100848-002', 'SHP-100848-003',
    'SI-100848-001', 'SI-100848-002', 'SI-100848-003'
]

exec_windows = []
for p in gt['processes']:
    for e in p['executions']:
        if e['case_id'] in missing_cids:
            exec_windows.append((e['case_id'], e['start_ts'], e['end_ts']))

chunk_dirs = sorted([p for p in base.iterdir() if p.is_dir() and 'chunk_' in p.name and (p / 'events.jsonl').exists()])
events = []
for c in chunk_dirs:
    with open(c / 'events.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
events.sort(key=lambda x: x.get('timestamp_ms', 0))

print('Inspecting events in windows of missing cases:')
for cid, st, et in exec_windows[:4]:
    print(f"\n=== Case {cid} ({st} -> {et}) ===")
    window_evs = [e for e in events if st <= e.get('timestamp_iso', '') <= (et or '9999')]
    # print unique window titles, extracted text snippets, or payloads
    titles = set(e.get('context', {}).get('active_app', {}).get('window_title', '') for e in window_evs)
    print('  Window titles:', titles)
    text_samples = []
    for e in window_evs:
        t = str(e.get('context', {}).get('extracted_text', ''))
        if len(t) > 10 and t not in text_samples:
            text_samples.append(t[:80])
    print('  Extracted text samples:', text_samples[:3])
