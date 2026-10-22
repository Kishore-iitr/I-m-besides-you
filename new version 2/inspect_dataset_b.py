import sys, json
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

b_dir = Path(r"G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_b")
sessions = sorted([d for d in b_dir.iterdir() if d.is_dir()])

print(f"Total sessions in dataset_b: {len(sessions)}")
for s in sessions:
    chunks = sorted([c for c in s.iterdir() if c.is_dir() and "chunk" in c.name])
    e_cnt = 0
    apps = set()
    for c in chunks:
        ev_file = c / "events.jsonl"
        if ev_file.exists():
            with open(ev_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        e_cnt += 1
                        try:
                            ev = json.loads(line)
                            app = (ev.get("context", {}) or {}).get("active_app", {}).get("app_name")
                            if app: apps.add(app)
                        except Exception:
                            pass
    print(f"Session {s.name:<36} | Events: {e_cnt:4} | Chunks: {len(chunks)} | Apps: {sorted(apps)[:4]}")
