import glob
import json
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

print("Examining keystrokes, clipboard, and events in sessions where expense_calc was open...")

checkpoint_files = glob.glob("checkpoints/checkpoint_*.json")

for cp in checkpoint_files:
    with open(cp, "r", encoding="utf-8") as fp:
        data = json.load(fp)
        events = data.get("clean_events", [])
        for ev in events:
            wt = ev.get("window_title", "")
            if "expense_calc" in wt.lower():
                etype = ev.get("event_type", "")
                text = ev.get("text", "") or ev.get("clipboard_text", "") or ev.get("key", "")
                if text or etype in ["clipboard_change", "key_down"]:
                    print(f"[{cp}] {etype} in {wt}: {text[:100]}")
