import json
import sys
from pathlib import Path
from datetime import datetime
from collections import Counter

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

DATASET_B_DIR = Path(r"G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_b")
PROFILING_FILE = Path(r"c:\Users\KISHORE S\Desktop\pulled_tmi\dataset_b_automation_profiling.json")

with open(PROFILING_FILE, "r", encoding="utf-8") as f:
    d = json.load(f)

segs = [s for s in d['all_segments_telemetry'] if 'payroll' in s.get('label', '').lower()]

sample_cases = [
    # Neela
    "PAYROLL-ITEMS-2026-001",
    "PAYROLL-ITEMS-2026-013",
    # Laptop
    "PAYROLL-ITEMS-2026-002",
    "PAYROLL-ITEMS-2026-004",
    "BATCH-W1",
    # Chaitanya
    "PAYROLL-ITEMS-2026-008",
    "PAYROLL-ITEMS-2026-012"
]

selected = [s for s in segs if s.get('case_id') in sample_cases]

chunk_cache = {}

for seg in selected:
    sid = seg["session_id"]
    cid = seg["case_id"]
    sdir = DATASET_B_DIR / sid
    st_ms = int(datetime.fromisoformat(seg["start"].replace("Z", "+00:00")).timestamp() * 1000)
    et_ms = int(datetime.fromisoformat(seg["end"].replace("Z", "+00:00")).timestamp() * 1000)
    
    if sid not in chunk_cache:
        chunks = sorted([p for p in sdir.iterdir() if p.is_dir() and "chunk" in p.name])
        evs = []
        for c in chunks:
            ef = c / "events.jsonl"
            if ef.exists():
                for line in open(ef, encoding="utf-8"):
                    if line.strip():
                        try:
                            item = json.loads(line)
                            item["_chunk"] = c.name
                            evs.append(item)
                        except Exception:
                            pass
        chunk_cache[sid] = evs
    
    session_evs = chunk_cache[sid]
    case_evs = [e for e in session_evs if st_ms <= e.get("timestamp_ms", 0) <= et_ms and e.get("layer") != "SYSTEM"]
    
    print(f"\n=======================================================")
    print(f"CASE: {cid} ({seg.get('label')}) | OP: {seg.get('operator')} | DUR: {seg.get('duration_seconds')}s")
    
    # print clicks with text
    clicks = []
    for e in case_evs:
        if "click" in e.get("event_type", ""):
            elem = (e.get("payload") or {}).get("element") or (e.get("payload") or {}).get("target_element") or {}
            txt = elem.get("text") or elem.get("name") or elem.get("automation_id") or ""
            if txt.strip():
                clicks.append(txt.strip())
    print(f"Clicks ({len(clicks)}): {clicks[:15]}")
    
    # print clipboard changes
    clips = []
    for e in case_evs:
        if e.get("event_type") == "clipboard_change":
            p = e.get("payload") or {}
            clips.append(f"len={p.get('text_length')}, fmt={p.get('formats_available')}")
    print(f"Clipboard events ({len(clips)}): {clips}")
    
    # print active window titles
    wins = set((e.get("context") or {}).get("active_app", {}).get("window_title", "") for e in case_evs)
    wins = [w for w in wins if w]
    print(f"Windows ({len(wins)}): {wins}")
