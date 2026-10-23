import json
import sys
from pathlib import Path
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

DATASET_B_DIR = Path(r"G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_b")
PROFILING_FILE = Path(r"c:\Users\KISHORE S\Desktop\pulled_tmi\dataset_b_automation_profiling.json")

with open(PROFILING_FILE, "r", encoding="utf-8") as f:
    d = json.load(f)

segs = [s for s in d['all_segments_telemetry'] if 'payroll' in s.get('label', '').lower()]

# Let's inspect PAYROLL-ITEMS-2026-002 and PAYROLL-ITEMS-2026-001
test_cases = [s for s in segs if s.get('case_id') in ['PAYROLL-ITEMS-2026-002', 'PAYROLL-ITEMS-2026-001', 'PAYROLL-ITEMS-2026-008', 'PO-2026-5097']]

for seg in test_cases[:2]:
    sid = seg["session_id"]
    cid = seg["case_id"]
    st = seg["start"]
    et = seg["end"]
    op = seg.get("operator")
    print(f"\n=======================================================")
    print(f"CASE: {cid} | Op: {op} | Dur: {seg['duration_seconds']}s | Session: {sid}")
    print(f"Time: {st} -> {et}")
    sdir = DATASET_B_DIR / sid
    
    st_ms = int(datetime.fromisoformat(st.replace("Z", "+00:00")).timestamp() * 1000)
    et_ms = int(datetime.fromisoformat(et.replace("Z", "+00:00")).timestamp() * 1000)
    
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
    evs.sort(key=lambda x: x.get("timestamp_ms", 0))
    case_evs = [e for e in evs if st_ms <= e.get("timestamp_ms", 0) <= et_ms and e.get("layer") != "SYSTEM"]
    print(f"Total Case Events: {len(case_evs)}")
    
    # summarize event types
    from collections import Counter
    c_types = Counter(e.get("event_type") for e in case_evs)
    print(f"Event counts: {dict(c_types)}")
    
    # print significant actions
    print("--- Significant Actions ---")
    for e in case_evs:
        et = e.get("event_type")
        payload = e.get("payload") or {}
        ctx = e.get("context") or {}
        act = ctx.get("active_app") or {}
        app_name = act.get("app_name") or act.get("process_name") or ""
        window_title = act.get("window_title") or ""
        
        if et in ("browser_click", "mouse_click"):
            elem = payload.get("element") or payload.get("target_element") or {}
            txt = elem.get("text") or elem.get("name") or elem.get("automation_id") or ""
            tag = elem.get("tag_name") or ""
            print(f"  [CLICK] app={app_name} | win={window_title[:35]} | tag={tag} | text='{txt.strip()}'")
        elif et == "clipboard_change":
            print(f"  [CLIPBOARD] app={app_name} | win={window_title[:35]} | len={payload.get('text_length')} | formats={payload.get('formats_available')}")
        elif et == "app_switch":
            new_app = (payload.get("new_app") or {}).get("app_name", "")
            new_title = (payload.get("new_app") or {}).get("window_title", "")
            print(f"  [SWITCH] {app_name} -> {new_app} ({new_title[:35]})")
        elif et == "browser_navigation":
            print(f"  [NAV] url={payload.get('url')}")
        elif et == "screenshot_smart":
            fname = (payload.get("file_reference") or {}).get("filename")
            reason = payload.get("trigger_reason")
            print(f"  [SCREENSHOT] {fname} trigger={reason}")
