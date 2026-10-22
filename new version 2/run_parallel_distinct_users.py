import sys
import time
import subprocess
import json
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PYTHON_EXE = r"C:\Users\KISHORE S\anaconda3\python.exe"
SCRIPT_PATH = r"c:\Users\KISHORE S\Desktop\pulled_tmi\run_complete_multistep_tmi.py"

SESSIONS = [
    {
        "operator": "MSI",
        "name": "msi",
        "session_id": "ses_20260701-053005-MSI",
        "session_dir": r"G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_a\ses_20260701-053005-MSI",
        "output_file": r"c:\Users\KISHORE S\Desktop\pulled_tmi\segments_msi.jsonl",
        "report_file": r"c:\Users\KISHORE S\Desktop\pulled_tmi\benchmark_msi.json",
        "log_file": r"c:\Users\KISHORE S\Desktop\pulled_tmi\run_msi.log"
    },
    {
        "operator": "CHAITANYA0BCF",
        "name": "chaitanya",
        "session_id": "ses_20260630-131729-CHAITANYA0BCF",
        "session_dir": r"G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_a\ses_20260630-131729-CHAITANYA0BCF",
        "output_file": r"c:\Users\KISHORE S\Desktop\pulled_tmi\segments_chaitanya.jsonl",
        "report_file": r"c:\Users\KISHORE S\Desktop\pulled_tmi\benchmark_chaitanya.json",
        "log_file": r"c:\Users\KISHORE S\Desktop\pulled_tmi\run_chaitanya.log"
    },
    {
        "operator": "Marcos",
        "name": "marcos",
        "session_id": "ses_20260701-062250-Marcos",
        "session_dir": r"G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_a\ses_20260701-062250-Marcos",
        "output_file": r"c:\Users\KISHORE S\Desktop\pulled_tmi\segments_marcos.jsonl",
        "report_file": r"c:\Users\KISHORE S\Desktop\pulled_tmi\benchmark_marcos.json",
        "log_file": r"c:\Users\KISHORE S\Desktop\pulled_tmi\run_marcos.log"
    },
    {
        "operator": "LAPTOP-0IM1OHQH",
        "name": "laptop0im",
        "session_id": "ses_20260701-075604-LAPTOP-0IM1OHQH",
        "session_dir": r"G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_a\ses_20260701-075604-LAPTOP-0IM1OHQH",
        "output_file": r"c:\Users\KISHORE S\Desktop\pulled_tmi\segments_laptop0im.jsonl",
        "report_file": r"c:\Users\KISHORE S\Desktop\pulled_tmi\benchmark_laptop0im.json",
        "log_file": r"c:\Users\KISHORE S\Desktop\pulled_tmi\run_laptop0im.log"
    }
]

def main():
    print("=" * 90)
    print("LAUNCHING 4 CONCURRENT TMI WORKERS FOR DISTINCT OPERATORS IN DATASET_A")
    print("=" * 90)
    for s in SESSIONS:
        print(f"  Operator: {s['operator']:<16} | Session: {s['session_id']}")
    print("=" * 90)

    t0 = time.time()
    procs = []
    log_fps = []

    for s in SESSIONS:
        log_fp = open(s["log_file"], "w", encoding="utf-8")
        log_fps.append(log_fp)
        cmd = [
            PYTHON_EXE,
            "-u",
            SCRIPT_PATH,
            "--session_dir", s["session_dir"],
            "--output_file", s["output_file"],
            "--report_file", s["report_file"]
        ]
        p = subprocess.Popen(cmd, stdout=log_fp, stderr=subprocess.STDOUT)
        procs.append((s, p, log_fp))
        print(f"[*] Worker started for '{s['operator']}' (PID {p.pid}). Output: {s['log_file']}")

    print("\nAll 4 worker processes running concurrently. Waiting for completion...\n")

    running = list(procs)
    finished = {}
    while running:
        time.sleep(3)
        still_running = []
        for s, p, lfp in running:
            ret = p.poll()
            if ret is None:
                still_running.append((s, p, lfp))
            else:
                elapsed = time.time() - t0
                lfp.close()
                status = "SUCCESS" if ret == 0 else f"FAILED (exit {ret})"
                print(f"[+] [{elapsed:6.1f}s] Worker for '{s['operator']}' (PID {p.pid}) finished: {status}")
                finished[s["name"]] = {"operator": s["operator"], "status": status, "exit_code": ret, "elapsed": elapsed}
        running = still_running

    total_parallel_time = time.time() - t0
    print("\n" + "=" * 90)
    print(f"ALL 4 WORKERS COMPLETED IN {total_parallel_time:.2f}s ({total_parallel_time/60:.2f} min)")
    print("=" * 90)

    aggregated = {
        "batch_type": "distinct_operators",
        "total_workers": len(SESSIONS),
        "total_parallel_wall_time_seconds": round(total_parallel_time, 2),
        "sessions": {}
    }

    sum_individual_times = 0.0
    for s in SESSIONS:
        rep_p = Path(s["report_file"])
        if rep_p.exists():
            with open(rep_p, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["operator"] = s["operator"]
                data["worker_elapsed_time"] = finished.get(s["name"], {}).get("elapsed", 0.0)
                sum_individual_times += data.get("timings", {}).get("Total End-to-End Pipeline Runtime", 0.0)
                aggregated["sessions"][s["name"]] = data
        else:
            aggregated["sessions"][s["name"]] = {
                "operator": s["operator"],
                "error": "Report file not generated",
                "worker_info": finished.get(s["name"], {})
            }

    aggregated["sum_individual_runtimes_seconds"] = round(sum_individual_times, 2)
    aggregated["parallel_speedup_factor"] = round(sum_individual_times / total_parallel_time, 2) if total_parallel_time > 0 else 1.0

    summary_file = Path(r"c:\Users\KISHORE S\Desktop\pulled_tmi\benchmark_parallel_distinct_summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(aggregated, f, indent=2, ensure_ascii=False)

    print(f"\n[Artifact Generated] Master summary saved to: {summary_file}")
    print(f"Sum of Individual Runtimes: {sum_individual_times:.2f}s")
    print(f"Parallel Wall-Clock Time:   {total_parallel_time:.2f}s")
    print(f"Parallel Throughput Gain:   {aggregated['parallel_speedup_factor']}x")

if __name__ == "__main__":
    main()
