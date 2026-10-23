import json
import sys
from pathlib import Path
import pytesseract
from PIL import Image

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
os_prefix = r'c:\Users\KISHORE S\Desktop\pulled_tmi\tessdata'
import os
os.environ['TESSDATA_PREFIX'] = os_prefix

DATASET_B_DIR = Path(r"G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_b")
PROFILING_FILE = Path(r"c:\Users\KISHORE S\Desktop\pulled_tmi\dataset_b_automation_profiling.json")

# Let's inspect session ses_20260701-175258-LAPTOP-76QMG9DE chunk_20260701-1730-LAPTOP-76QMG9DE
sdir = DATASET_B_DIR / "ses_20260701-175258-LAPTOP-76QMG9DE"
chunk = sdir / "chunk_20260701-1730-LAPTOP-76QMG9DE"
scrs_dir = chunk / "screenshots"

if scrs_dir.exists():
    sample_images = sorted(list(scrs_dir.glob("*.jpg")))[:6]
    print(f"Found {len(sample_images)} sample images.")
    for img_p in sample_images:
        print(f"\n--- OCR for {img_p.name} ---")
        img = Image.open(img_p)
        txt = pytesseract.image_to_string(img, lang="jpn+eng")
        lines = [l.strip() for l in txt.splitlines() if len(l.strip()) > 2]
        for l in lines[:12]:
            print("  ", l)
