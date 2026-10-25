import sys, json
from pathlib import Path
from datetime import datetime

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

DATASET_B_DIR = Path(r"G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_b")

with open(r"c:\Users\KISHORE S\Desktop\pulled_tmi\dataset_b_automation_profiling.json", encoding="utf-8") as f:
    d = json.load(f)

invoice_segs = [s for s in d["all_segments_telemetry"] if "invoice" in s["label"].lower()]

# Select 3 representative invoice cases from different operators
sample_cases = [invoice_segs[0], invoice_segs[10], invoice_segs[20]]

for idx, seg in enumerate(sample_cases, 1):
    sid = seg["session_id"]
    cid = seg["case_id"]
    st = seg["start"]
    et = seg["end"]
    sdir = DATASET_B_DIR / sid
    
    st_ms = int(datetime.fromisoformat(st.replace("Z", "+00:00")).timestamp() * 1000)
    et_ms = int(datetime.fromisoformat(et.replace("Z", "+00:00")).timestamp() * 1000)
    
    # Load raw events for this session
    chunks = sorted([p for p in sdir.iterdir() if p.is_dir() and "chunk" in p.name])
    all_evs = []
    for c in chunks:
        ef = c / "events.jsonl"
        if ef.exists():
            for line in open(ef, encoding="utf-8"):
                if line.strip():
                    ev = json.loads(line)
                    ev["_chunk"] = c.name
                    all_evs.append(ev)
    all_evs.sort(key=lambda x: x.get("timestamp_ms", 0))
    
    case_evs = [e for e in all_evs if st_ms <= e.get("timestamp_ms", 0) <= et_ms and e.get("layer") != "SYSTEM"]
    
    print("=" * 90)
    print(f"CASE {idx}: {cid} ({seg['label']}) in session {sid}")
    print(f"Time Window: {st} -> {et} ({seg['duration_seconds']}s) | Total Events: {len(case_evs)}")
    print("=" * 90)
    
    for e in case_evs:
        t = e.get("timestamp_iso", "").split("T")[-1]
        etype = e.get("event_type")
        payload = e.get("payload") or {}
        ctx = e.get("context") or {}
        act = ctx.get("active_app") or {}
        app = act.get("app_name") or act.get("process_name") or ""
        title = act.get("window_title") or ""
        
        detail = ""
        if etype == "browser_navigation":
            detail = f"NAV -> {payload.get('url')}"
        elif etype in ("browser_click", "mouse_click"):
            el = payload.get("element") or payload.get("target_element") or {}
            txt = el.get("text") or el.get("name") or el.get("automation_id") or ""
            coords = payload.get("click_coordinates") or payload.get("coordinates") or {}
            detail = f"CLICK on [{txt}] @ {coords}"
        elif etype == "keystroke":
            detail = f"KEY [{payload.get('key')}] char='{payload.get('character')}'"
        elif etype == "clipboard_change":
            detail = f"CLIPBOARD -> {json.dumps(payload, ensure_ascii=False)[:80]}"
        elif etype == "app_switch":
            detail = f"SWITCH -> {payload.get('new_app', {}).get('app_name')} ({payload.get('new_app', {}).get('window_title')[:40]})"
        elif etype == "screenshot_smart":
            fname = (payload.get("file_reference") or {}).get("filename")
            detail = f"SCREENSHOT: {fname}"
        
        if detail:
            print(f"  {t} | {app:<16} | {etype:<20} | {detail}")
