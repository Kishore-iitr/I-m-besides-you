import json
from pathlib import Path
from PIL import Image
import pytesseract, os

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
os.environ['TESSDATA_PREFIX'] = r'c:\Users\KISHORE S\Desktop\pulled_tmi\tessdata'

base = Path(r'G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_a\ses_20260701-043922-SIDDHIGUPTAB00B')
chunk_dirs = sorted([p for p in base.iterdir() if p.is_dir() and 'chunk_' in p.name and (p / 'events.jsonl').exists()])

# Search for screenshots between 04:57:43 and 04:58:35 (SI-100848-001)
st = '2026-07-01T04:57:43'
et = '2026-07-01T04:58:35'
for c in chunk_dirs:
    with open(c / 'events.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            if 'screenshot_smart' in line:
                d = json.loads(line)
                ts = d.get('timestamp_iso', '')
                if st <= ts <= et:
                    rel = (d.get('payload') or {}).get('file_reference', {}).get('relative_path')
                    p = c / rel if rel else None
                    if p and p.exists():
                        txt = pytesseract.image_to_string(Image.open(p), lang='jpn+eng')
                        meaningful = [l.strip() for l in txt.split('\n') if len(l.strip()) >= 3 and not l.strip().isdigit()][:5]
                        print(f"Screenshot at {ts} ({p.name}): {meaningful}")
                        break
