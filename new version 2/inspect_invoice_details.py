import sys, json
from pathlib import Path
from datetime import datetime
import pytesseract
from PIL import Image

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

DATASET_B_DIR = Path(r"G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_b")
sdir = DATASET_B_DIR / "ses_20260701-175258-LAPTOP-76QMG9DE"
chunk = sdir / "chunk_20260701-1800-LAPTOP-76QMG9DE"
ef = chunk / "events.jsonl"

print("--- EXAMINING INVOICE PROCESSING CLIPBOARD & OCR ---")
for line in open(ef, encoding="utf-8"):
    if not line.strip(): continue
    ev = json.loads(line)
    ts = ev.get("timestamp_iso", "")
    if "18:02:25" <= ts <= "18:02:50":
        etype = ev.get("event_type")
        payload = ev.get("payload") or {}
        if etype == "clipboard_change":
            print(f"{ts} | CLIPBOARD: {json.dumps(payload, ensure_ascii=False)}")
        elif etype == "screenshot_smart":
            fname = (payload.get("file_reference") or {}).get("filename")
            img_p = chunk / "screenshots" / fname
            if img_p.exists():
                txt = pytesseract.image_to_string(Image.open(img_p), lang="jpn+eng")
                lines = [l.strip() for l in txt.splitlines() if len(l.strip()) > 2]
                print(f"{ts} | SCREENSHOT {fname}: {lines[:5]}")
