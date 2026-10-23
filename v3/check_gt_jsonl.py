import json, sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

base = Path(r'G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_a\ses_20260701-043922-SIDDHIGUPTAB00B')
with open(base / 'gt.jsonl', 'r', encoding='utf-8') as f:
    for i in range(10):
        l = f.readline()
        if l:
            d = json.loads(l)
            print(f"Line {i+1}: {d}")
