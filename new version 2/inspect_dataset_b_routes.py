import sys, json, re
from pathlib import Path
from collections import Counter

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

b_dir = Path(r"G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_b")
sessions = sorted([d for d in b_dir.iterdir() if d.is_dir()])

url_counter = Counter()
case_counter = Counter()
UNIVERSAL_CASE_REGEX = re.compile(r'(?:([A-Z]{2,6})[-_](\d{4,8})[-_](\d{2,5})|(BATCH[-_]W\d+))\b')

for s in sessions:
    chunks = sorted([c for c in s.iterdir() if c.is_dir() and "chunk" in c.name])
    for c in chunks:
        ev_file = c / "events.jsonl"
        if ev_file.exists():
            with open(ev_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            ev = json.loads(line)
                            etype = ev.get("event_type")
                            payload = ev.get("payload", {})
                            if etype == "browser_navigation":
                                url = payload.get("url", "")
                                if url:
                                    url_counter[url] += 1
                            txt = json.dumps(ev, ensure_ascii=False)
                            for m in UNIVERSAL_CASE_REGEX.finditer(txt):
                                cid = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m.group(1) else m.group(4)
                                case_counter[cid] += 1
                        except Exception:
                            pass

print("=== TOP URLS VISITED IN DATASET B ===")
for u, cnt in url_counter.most_common(20):
    print(f"  {cnt:4}x | {u}")

print("\n=== CASE PREFIXES OBSERVED IN DATASET B ===")
prefix_counts = Counter()
for cid, cnt in case_counter.items():
    pfx = cid.split("-")[0]
    prefix_counts[pfx] += cnt
for pfx, cnt in prefix_counts.most_common(20):
    print(f"  {cnt:4}x | {pfx}")
