import json
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open("dataset_b_automation_profiling.json", "r", encoding="utf-8") as f:
    d = json.load(f)

print("=== Ranked Automation Candidates ===")
candidates = d.get("ranked_automation_candidates", [])
for idx, c in enumerate(candidates, 1):
    print(f"{idx}. {c.get('process_name')} | Score: {c.get('automation_priority_score')} | Executions: {c.get('total_executions')} | Total Duration: {c.get('total_duration_seconds')}s")

print("\n=== Candidate 2 Details ===")
if len(candidates) >= 2:
    print(json.dumps(candidates[1], indent=2, ensure_ascii=False))

all_segs = d.get("all_segments_telemetry", [])
payroll_segs = [s for s in all_segs if "payroll" in s.get("label", "").lower()]
print(f"\nTotal payroll segments found in all_segments_telemetry: {len(payroll_segs)}")

ops = set(s.get("operator") for s in payroll_segs)
print(f"Operators: {ops}")

for s in payroll_segs:
    print(f"  Op: {s.get('operator'):<16} | Case: {s.get('case_id'):<25} | Dur: {s.get('duration_seconds'):5.1f}s | Session: {s.get('session_id')}")
