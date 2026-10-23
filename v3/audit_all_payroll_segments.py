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

print(f"Total payroll segments: {len(segs)}")
chunk_cache = {}

for s in segs:
    sid = s["session_id"]
    sdir = DATASET_B_DIR / sid
    st_ms = int(datetime.fromisoformat(s["start"].replace("Z", "+00:00")).timestamp() * 1000)
    et_ms = int(datetime.fromisoformat(s["end"].replace("Z", "+00:00")).timestamp() * 1000)
    
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
    screenshots = [e for e in case_evs if e.get("event_type") == "screenshot_smart"]
    clicks = [e for e in case_evs if "click" in e.get("event_type", "")]
    inputs = [e for e in case_evs if e.get("event_type") in ("keystroke", "browser_form_input", "clipboard_change")]
    apps = set((e.get("context") or {}).get("active_app", {}).get("app_name") for e in case_evs)
    apps.discard(None)
    apps.discard("")
    
    print(f"[{s.get('operator')}] {s.get('case_id')} ({s.get('label')}) | Dur: {s.get('duration_seconds')}s | Evs: {len(case_evs)} | Scrs: {len(screenshots)} | Clicks: {len(clicks)} | Apps: {sorted(list(apps))}")
