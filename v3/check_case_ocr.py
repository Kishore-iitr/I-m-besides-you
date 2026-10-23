import json
import sys
from pathlib import Path
from datetime import datetime
import pytesseract
from PIL import Image

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
import os
os.environ['TESSDATA_PREFIX'] = r'c:\Users\KISHORE S\Desktop\pulled_tmi\tessdata'

DATASET_B_DIR = Path(r"G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_b")
PROFILING_FILE = Path(r"c:\Users\KISHORE S\Desktop\pulled_tmi\dataset_b_automation_profiling.json")

with open(PROFILING_FILE, "r", encoding="utf-8") as f:
    d = json.load(f)

# Find PAYROLL-ITEMS-2026-002
p2 = [s for s in d['all_segments_telemetry'] if s.get('case_id') == 'PAYROLL-ITEMS-2026-002'][0]
sid = p2['session_id']
sdir = DATASET_B_DIR / sid
st_ms = int(datetime.fromisoformat(p2["start"].replace("Z", "+00:00")).timestamp() * 1000)
et_ms = int(datetime.fromisoformat(p2["end"].replace("Z", "+00:00")).timestamp() * 1000)

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

case_evs = [e for e in evs if st_ms <= e.get("timestamp_ms", 0) <= et_ms and e.get("layer") != "SYSTEM"]
screenshots = [e for e in case_evs if e.get("event_type") == "screenshot_smart"]
print(f"PAYROLL-ITEMS-2026-002 has {len(screenshots)} screenshots between {st_ms} and {et_ms}")

# Sample 4 screenshots: 1st, 1/3, 2/3, and last
idx_samples = [0, len(screenshots)//3, 2*len(screenshots)//3, len(screenshots)-1]
for i in idx_samples:
    sc = screenshots[i]
    fname = (sc.get('payload') or {}).get('file_reference', {}).get('filename')
    chunk = sc.get('_chunk')
    ipath = sdir / chunk / "screenshots" / fname
    print(f"\n--- Screenshot {i}: {fname} (exists: {ipath.exists()}) ---")
    if ipath.exists():
        img = Image.open(ipath)
        txt = pytesseract.image_to_string(img, lang="jpn+eng")
        lines = [l.strip() for l in txt.splitlines() if len(l.strip()) > 2]
        for l in lines[:15]:
            print("  ", l)
