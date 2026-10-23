import json, re
from pathlib import Path

base = Path(r'G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_a\ses_20260701-043922-SIDDHIGUPTAB00B')
chunk_dirs = sorted([p for p in base.iterdir() if p.is_dir() and 'chunk_' in p.name and (p / 'events.jsonl').exists()])

print('Searching for 100848 occurrences across events.jsonl:')
found_100848 = set()
for c in chunk_dirs:
    with open(c / 'events.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            for m in re.finditer(r'[A-Za-z0-9_\-]+100848[A-Za-z0-9_\-]*', line):
                found_100848.add(m.group(0))

print(f"Found {len(found_100848)} patterns matching 100848:")
print(sorted(list(found_100848)))
