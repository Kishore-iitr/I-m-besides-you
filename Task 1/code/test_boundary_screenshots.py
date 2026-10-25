import json
import re
import sys
from pathlib import Path
from datetime import datetime, timezone

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

DATASET_B_DIR = Path(r"G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_b")
SEGMENTS_FILE = Path(r"c:\Users\KISHORE S\Desktop\pulled_tmi\task one\segments.json")

def to_epoch(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()

def to_iso(sec):
    return datetime.fromtimestamp(sec, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

with open(SEGMENTS_FILE, "r", encoding="utf-8") as f:
    segments = json.load(f)

# Test on session 1
s1_id = "ses_20260701-164424-CHAITANYA0BCF"
s1_segs = [s for s in segments if s["session_id"] == s1_id]

s_dir = DATASET_B_DIR / s1_id
chunk_dirs = sorted([p for p in s_dir.iterdir() if p.is_dir() and "chunk" in p.name])

# Collect screenshots
shots = []
for cdir in chunk_dirs:
    sdir = cdir / "screenshots"
    if sdir.exists():
        for p in sorted(sdir.glob("*.jpg")) + sorted(sdir.glob("*.png")):
            # Extract timestamp from filename
            m = re.search(r'scr_smart_(\d{13})_', p.name)
            if m:
                sec = int(m.group(1)) / 1000.0
                shots.append((sec, p.name, cdir.name))

shots.sort(key=lambda x: x[0])
print(f"Total screenshots in {s1_id}: {len(shots)}")

# Load events for rich context
events = []
for cdir in chunk_dirs:
    ev_file = cdir / "events.jsonl"
    if ev_file.exists():
        with open(ev_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line.strip()))
events.sort(key=lambda x: x.get("timestamp_ms", 0))

# For first 3 segments, inspect before and after end
for idx, seg in enumerate(s1_segs[:3]):
    st_sec = to_epoch(seg["start"])
    et_sec = to_epoch(seg["end"])
    lbl = seg["label"]
    
    # Screenshots during segment, especially near end (et_sec - 5s to et_sec)
    shots_inside = [s for s in shots if st_sec <= s[0] <= et_sec]
    shots_near_end = [s for s in shots if et_sec - 5.0 <= s[0] <= et_sec]
    if not shots_near_end and shots_inside:
        shots_near_end = [shots_inside[-1]]
        
    # Screenshots immediately after end (et_sec to et_sec + 8s)
    shots_after_end = [s for s in shots if et_sec < s[0] <= et_sec + 8.0]
    
    print(f"\n--- Segment {idx+1}: {lbl} ({seg['start']} -> {seg['end']}, {et_sec - st_sec:.1f}s) ---")
    print(f"  Shots inside: {len(shots_inside)}, near end: {len(shots_near_end)}, after end: {len(shots_after_end)}")
    
    if shots_near_end:
        last_shot = shots_near_end[-1]
        # Find closest event to last_shot
        ev_near = min(events, key=lambda e: abs(e.get("timestamp_ms", 0)/1000.0 - last_shot[0]))
        w_title = (ev_near.get("context") or {}).get("active_app", {}).get("window_title") or ""
        url = (ev_near.get("payload") or {}).get("url") or ""
        print(f"  BEFORE END Shot: {last_shot[1]} (at {to_iso(last_shot[0])})")
        print(f"    Window: {w_title[:50]} | URL: {url}")
        
    if shots_after_end:
        first_after = shots_after_end[0]
        ev_after = min(events, key=lambda e: abs(e.get("timestamp_ms", 0)/1000.0 - first_after[0]))
        w_title = (ev_after.get("context") or {}).get("active_app", {}).get("window_title") or ""
        url = (ev_after.get("payload") or {}).get("url") or ""
        print(f"  AFTER END Shot : {first_after[1]} (at {to_iso(first_after[0])})")
        print(f"    Window: {w_title[:50]} | URL: {url}")
