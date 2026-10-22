import sys, json

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

with open(r"c:\Users\KISHORE S\Desktop\pulled_tmi\dataset_b_automation_profiling.json", encoding="utf-8") as f:
    d = json.load(f)

invoice_segs = [s for s in d["all_segments_telemetry"] if "invoice" in s["label"].lower()]
print(f"Total Invoice Segments Recovered in Dataset B: {len(invoice_segs)}")

by_session = {}
for s in invoice_segs:
    by_session.setdefault(s["session_id"], []).append(s)

print(f"Distributed across {len(by_session)} sessions:")
for sid, segs in sorted(by_session.items()):
    cases = [s["case_id"] for s in segs]
    durations = [s["duration_seconds"] for s in segs]
    print(f"  {sid}: {len(segs):2d} invoice cases | Total: {sum(durations):5.1f}s | Sample cases: {cases[:4]}")
