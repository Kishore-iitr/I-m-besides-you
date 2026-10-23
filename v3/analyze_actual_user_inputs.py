import glob
import json
import collections
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

invoice_apps = collections.Counter()
invoice_windows = collections.Counter()
invoice_docs = collections.Counter()

payroll_apps = collections.Counter()
payroll_windows = collections.Counter()
payroll_docs = collections.Counter()

other_workflows = collections.defaultdict(lambda: {"apps": collections.Counter(), "windows": collections.Counter()})

reports = glob.glob("checkpoints/report_*.json")
print(f"Analyzing {len(reports)} session reports...")

for r in reports:
    with open(r, "r", encoding="utf-8") as fp:
        data = json.load(fp)
        for seg in data.get("segments", []):
            label = seg.get("label", "unknown")
            telemetry = seg.get("automation_telemetry", {})
            apps = telemetry.get("active_applications", [])
            windows = telemetry.get("window_titles", [])
            
            if label == "invoice_processing":
                for a in apps: invoice_apps[a] += 1
                for w in windows:
                    invoice_windows[w] += 1
                    if ".doc" in w.lower() or ".xls" in w.lower() or ".txt" in w.lower():
                        invoice_docs[w] += 1
            elif "payroll" in label:
                for a in apps: payroll_apps[a] += 1
                for w in windows:
                    payroll_windows[w] += 1
                    if ".doc" in w.lower() or ".xls" in w.lower() or ".txt" in w.lower():
                        payroll_docs[w] += 1
            else:
                for a in apps: other_workflows[label]["apps"][a] += 1
                for w in windows: other_workflows[label]["windows"][w] += 1

print("\n" + "="*70)
print("1. INVOICE PROCESSING (財務会計システム) - APPLICATIONS USED:")
for a, c in invoice_apps.most_common():
    print(f"   - {a}: {c} occurrences")

print("\nINVOICE PROCESSING - DOCUMENTS / WINDOW TITLES ACCESSED:")
for w, c in invoice_windows.most_common():
    print(f"   - {w}: {c} occurrences")

print("\n" + "="*70)
print("2. PAYROLL ITEM PROCESSING (HR人事給与システム) - APPLICATIONS USED:")
for a, c in payroll_apps.most_common():
    print(f"   - {a}: {c} occurrences")

print("\nPAYROLL ITEM PROCESSING - DOCUMENTS / WINDOW TITLES ACCESSED:")
for w, c in payroll_windows.most_common():
    print(f"   - {w}: {c} occurrences")

print("\n" + "="*70)
print("3. OTHER WORKFLOWS IN DATASET B:")
for wf, d in other_workflows.items():
    print(f"\nWorkflow '{wf}':")
    print("   Apps:", dict(d["apps"].most_common(5)))
    print("   Windows:", dict(d["windows"].most_common(5)))
