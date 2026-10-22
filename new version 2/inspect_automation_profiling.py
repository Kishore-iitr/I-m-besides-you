import sys, json

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

with open(r"c:\Users\KISHORE S\Desktop\pulled_tmi\dataset_b_automation_profiling.json", encoding="utf-8") as f:
    d = json.load(f)

print("=" * 90)
print("DATASET B AUTOMATION CANDIDATE DISCOVERY SUMMARY (FOR STEP 2)")
print("=" * 90)
print(f"Total Dataset Sessions:        {d['total_sessions']}")
print(f"Total Work Segments Recovered: {d['total_segments_recovered']}")
print(f"Total Active Work Time:        {d['total_work_duration_hours']:.2f} hours ({d['total_work_duration_seconds']:.1f} seconds)")
print(f"Total Pipeline Runtime:        {d['total_parallel_wall_time_seconds']:.2f}s")
print("=" * 90)

print("\n--- RANKED AUTOMATION CANDIDATES ---")
print(f"{'Rank':<4} {'Process Label':<35} {'Cases':>5} {'Time(m)':>8} {'% Work':>7} {'Avg Keystr':>10} {'Avg Clicks':>10} {'Cross-Sys %':>11} {'Priority':>9}")
print("-" * 105)

for rank, (lbl, info) in enumerate(d["processes_ranked_by_priority"][:12], 1):
    cnt = info["execution_count"]
    tot_m = info["total_duration_minutes"]
    pct = info["percentage_of_total_work_time"]
    avg_k = info["average_keystrokes_per_case"]
    avg_c = info["average_clicks_per_case"]
    cs_pct = info["cross_system_transfer_rate_pct"]
    p_score = info["automation_priority_score"]
    print(f"{rank:02d}.  {lbl:<35} {cnt:>5} {tot_m:>7.1f}m {pct:>6.1f}% {avg_k:>10.1f} {avg_c:>10.1f} {cs_pct:>10.1f}% {p_score:>9.2f}")

print("\n--- OPERATOR WORKLOAD BREAKDOWN ---")
op_workload = {}
for s in d["all_segments_telemetry"]:
    op = s.get("operator", "unknown")
    dur = s.get("duration_seconds", 0)
    op_workload.setdefault(op, {"count": 0, "seconds": 0.0})
    op_workload[op]["count"] += 1
    op_workload[op]["seconds"] += dur

for op, info in sorted(op_workload.items(), key=lambda x: x[1]["seconds"], reverse=True):
    print(f"  Operator {op:<20}: {info['count']:>3} cases | {info['seconds']/60.0:>6.1f} mins ({info['seconds']/d['total_work_duration_seconds']*100:>5.1f}% of total work)")
