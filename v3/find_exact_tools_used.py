import glob
import json
import os
import re

print("Searching checkpoints for applications and files used in invoice_processing vs payroll...")

workflow_apps = {}
workflow_files = {}

for f in glob.glob("checkpoints/report_*.json"):
    try:
        with open(f, "r", encoding="utf-8") as fp:
            data = json.load(fp)
            # Inspect structure
            for wf in data.get("workflows", []):
                name = wf.get("name") or wf.get("label") or "unknown"
                apps = wf.get("applications", [])
                files = wf.get("files", [])
                workflow_apps.setdefault(name, set()).update(apps)
                workflow_files.setdefault(name, set()).update(files)
    except Exception as e:
        pass

for f in glob.glob("checkpoints/stage1_activities_*.json"):
    try:
        with open(f, "r", encoding="utf-8") as fp:
            data = json.load(fp)
            activities = data if isinstance(data, list) else data.get("activities", [])
            for act in activities:
                name = act.get("predicted_label") or act.get("label") or act.get("category") or "unknown"
                for ev in act.get("events", []):
                    wt = ev.get("window_title") or ev.get("title") or ""
                    if wt:
                        workflow_apps.setdefault(name, set()).add(wt)
    except Exception as e:
        pass

print("\n--- DETECTED WORKFLOWS & WINDOWS/FILES ---")
for wf, items in workflow_apps.items():
    print(f"\nWorkflow: {wf} (Total items: {len(items)})")
    for item in sorted(list(items))[:25]:
        print(f"   - {item}")

print("\n--- DETECTED FILES ---")
for wf, files in workflow_files.items():
    print(f"Workflow: {wf} -> Files: {files}")
