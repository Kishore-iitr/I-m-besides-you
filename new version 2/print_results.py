import sys, json

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

with open(r"c:\Users\KISHORE S\Desktop\pulled_tmi\benchmark_parallel_distinct_summary.json", encoding="utf-8") as f:
    data = json.load(f)

print("=" * 90)
print("PARALLEL BENCHMARK REPORT - 4 DISTINCT OPERATORS")
print("=" * 90)
print(f"Total Parallel Wall Time:       {data.get('total_parallel_wall_time_seconds')}s ({data.get('total_parallel_wall_time_seconds')/60:.2f} min)")
print(f"Cumulative Individual Runtime: {data.get('sum_individual_runtimes_seconds')}s ({data.get('sum_individual_runtimes_seconds')/60:.2f} min)")
print(f"Parallel Speedup Factor:        {data.get('parallel_speedup_factor')}x")
print("=" * 90)

for name, s in data.get("sessions", {}).items():
    op = s.get("operator")
    sid = s.get("session_id")
    raw_ev = s.get("total_events_loaded")
    clean_ev = s.get("clean_events_loaded")
    preds = s.get("predicted_segments_count")
    gts = s.get("ground_truth_executions_count")
    tot_time = s.get("timings", {}).get("Total End-to-End Pipeline Runtime", 0)
    worker_elapsed = s.get("worker_elapsed_time", 0)
    
    print(f"\nOperator: {op} ({name})")
    print(f"Session ID: {sid}")
    print(f"Events: {raw_ev} raw -> {clean_ev} clean user events")
    print(f"Segment Count: {preds} predicted vs {gts} Ground Truth executions (Discovery: {preds}/{gts})")
    print(f"Wall-Clock Elapsed: {worker_elapsed:.1f}s | Pipeline Internal Timing: {tot_time:.1f}s")
    
    print("Boundary Tolerance Metrics:")
    bm = s.get("boundary_metrics", {})
    for k in ["tol_1s", "tol_2s", "tol_5s", "tol_10s", "tol_30s"]:
        m = bm.get(k, {})
        tol = m.get("tolerance_s")
        tp = m.get("tp")
        prec = m.get("precision")
        rec = m.get("recall")
        f1 = m.get("f1")
        print(f"  <= {tol:>2}s: TP={tp:>2}/{gts} | Precision={prec:5.1f}% | Recall={rec:5.1f}% | F1={f1:5.1f}%")
        
    print("\nLayer & Process Timings:")
    timings = s.get("timings", {})
    for layer, dur in timings.items():
        if layer != "Total End-to-End Pipeline Runtime":
            print(f"  - {layer:<55}: {dur:6.2f}s")

    print("\nProcess Alignment Mapping:")
    align = s.get("process_alignment", {})
    for proc, info in align.items():
        print(f"  * {proc:<32} -> {info.get('gt_family')} (Matches: {info.get('matches')})")
    print("-" * 90)
