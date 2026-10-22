import sys, json
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

cdir = Path(r"G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_a\ses_20260701-053005-MSI\chunk_20260701-0530-MSI")
events = [json.loads(line) for line in open(cdir / "events.jsonl", encoding="utf-8") if line.strip()]

for ev in events:
    ts = ev.get("timestamp_iso", "")
    if "2026-07-01T05:32:50" <= ts <= "2026-07-01T05:35:00":
        etype = ev.get("event_type")
        payload = ev.get("payload", {})
        if etype in ("browser_navigation", "browser_click", "mouse_click", "app_switch"):
            p_str = json.dumps(payload, ensure_ascii=False)[:120]
            print(f"{ts} | {etype:<18} | {p_str}")
