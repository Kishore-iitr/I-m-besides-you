import glob
import json
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

print("Inspecting segments with 'expense_calc - Excel'...")

for f in glob.glob("checkpoints/report_*.json"):
    with open(f, "r", encoding="utf-8") as fp:
        data = json.load(fp)
        for seg in data.get("segments", []):
            telemetry = seg.get("automation_telemetry", {})
            windows = telemetry.get("window_titles", [])
            if any("excel" in w.lower() or "expense_calc" in w.lower() for w in windows):
                print("\nSession:", seg.get("session_id"), "| Case:", seg.get("case_id"), "| Label:", seg.get("label"))
                print("Objective:", seg.get("objective"))
                print("Additional Context:", seg.get("additional_context"))
                print("Window titles:", windows)
