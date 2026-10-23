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

reports = glob.glob("checkpoints/report_*.json")
inv_segments = []

for r in reports:
    with open(r, "r", encoding="utf-8") as fp:
        data = json.load(fp)
        for seg in data.get("segments", []):
            if seg.get("label") == "invoice_processing" or seg.get("label") == "invoice_approval":
                inv_segments.append(seg)

print(f"Total Invoice Processing Segments: {len(inv_segments)}")

doc_counts = collections.Counter()
app_counts = collections.Counter()

for seg in inv_segments:
    telemetry = seg.get("automation_telemetry", {})
    apps = telemetry.get("active_applications", [])
    windows = telemetry.get("window_titles", [])
    for a in apps:
        app_counts[a] += 1
    for w in windows:
        for term in ["word", "excel", "notepad", "ichiran", "calc", "kitei"]:
            if term in w.lower():
                doc_counts[w] += 1

print("\n--- APPLICATIONS USED IN REAL INVOICE PROCESSING ---")
for a, c in app_counts.most_common():
    print(f"  {a}: {c} ({c/len(inv_segments)*100:.1f}%)")

print("\n--- SUPPORTING DOCUMENTS / WINDOWS IN REAL INVOICE PROCESSING ---")
for w, c in doc_counts.most_common():
    print(f"  {w}: {c}")
