import json, re
from pathlib import Path
from collections import Counter

base = Path(r'G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_a\ses_20260701-043922-SIDDHIGUPTAB00B')
chunk_dirs = sorted([p for p in base.iterdir() if p.is_dir() and 'chunk' in p.name and (p / 'events.jsonl').exists()])

three_part = Counter()
for c in chunk_dirs:
    with open(c / 'events.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            for m in re.finditer(r'\b([A-Z]{2,6})[-_](\d{4,8})[-_](\d{2,4})\b', line):
                three_part[m.group(0)] += 1

print('Top three part IDs found in Siddhi events.jsonl:')
for k, v in three_part.most_common(40):
    print(f"  {k}: {v}")
