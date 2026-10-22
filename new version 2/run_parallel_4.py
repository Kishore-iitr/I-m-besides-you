import sys
import time
import subprocess
import json
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

PYTHON_EXE = r"C:\Users\KISHORE S\anaconda3\python.exe"
SCRIPT_PATH = r"c:\Users\KISHORE S\Desktop\pulled_tmi\run_complete_multistep_tmi.py"

SESSIONS = [
    {
        "name": "yuvraj",
        "session_dir": r"G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_a\ses_20260701-172430-yuvraj",
        "output_file": r"c:\Users\KISHORE S\Desktop\pulled_tmi\segments_yuvraj.jsonl",
        "report_file": r"c:\Users\KISHORE S\Desktop\pulled_tmi\benchmark_yuvraj.json",
        "log_file": r"c:\Users\KISHORE S\Desktop\pulled_tmi\run_yuvraj.log"
    },
    {
        "name": "laptop_r36",
        "session_dir": r"G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_a\ses_20260701-063106-LAPTOP-R36BQBTE",
        "output_file": r"c:\Users\KISHORE S\Desktop\pulled_tmi\segments_laptop_r36.jsonl",
        "report_file": r"c:\Users\KISHORE S\Desktop\pulled_tmi\benchmark_laptop_r36.json",
        "log_file": r"c:\Users\KISHORE S\Desktop\pulled_tmi\run_laptop_r36.log"
    },
    {
        "name": "siddhi_053720",
        "session_dir": r"G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_a\ses_20260701-053720-SIDDHIGUPTAB00B",
        "output_file": r"c:\Users\KISHORE S\Desktop\pulled_tmi\segments_siddhi_053720.jsonl",
        "report_file": r"c:\Users\KISHORE S\Desktop\pulled_tmi\benchmark_siddhi_053720.json",
        "log_file": r"c:\Users\KISHORE S\Desktop\pulled_tmi\run_siddhi_053720.log"
    },
    {
        "name": "siddhi_163424",
        "session_dir": r"G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_a\ses_20260630-163424-SIDDHIGUPTAB00B",
        "output_file": r"c:\Users\KISHORE S\Desktop\pulled_tmi\segments_siddhi_163424.jsonl",
        "report_file": r"c:\Users\KISHORE S\Desktop\pulled_tmi\benchmark_siddhi_163424.json",
        "log_file": r"c:\Users\KISHORE S\Desktop\pulled_tmi\run_siddhi_163424.log"
    }
]

def main():
    print("=" * 80)
    print("LAUNCHING 4 PARALLEL TMI PIPELINE SESSIONS ON DATASET_A")
    print("=" * 80)
    for s in SESSIONS:
        print(f"Session: {s['name']:<15} | Dir: {Path(s['session_dir']).name}")
    print("=" * 80)

    t0 = time.time()
    procs = []
    log_fps = []

    for s in SESSIONS:
        log_fp = open(s["log_file"], "w", encoding="utf-8")
        log_fps.append(log_fp)
        cmd = [
            PYTHON_EXE,
            SCRIPT_PATH,
            "--session_dir", s["session_dir"],
            "--output_file", s["output_file"],
            "--report_file", s["report_file"]
        ]
        p = subprocess.Popen(cmd, stdout=log_fp, stderr=subprocess.STDOUT)
        procs.append((s, p, log_fp))
        print(f"[*] Started process for {s['name']} (PID {p.pid}). Logging to {s['log_file']}")

    print("\nAll 4 processes launched in parallel. Monitoring progress...\n")

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
                print(f"[+] [{elapsed:6.1f}s] Process {s['name']} (PID {p.pid}) finished: {status}")
                finished[s["name"]] = {"status": status, "exit_code": ret, "elapsed": elapsed}
        running = still_running

    total_parallel_time = time.time() - t0
    print("\n" + "=" * 80)
    print(f"ALL 4 SESSIONS COMPLETED IN {total_parallel_time:.2f}s ({total_parallel_time/60:.2f} min)")
    print("=" * 80)

    # Aggregate benchmark reports
    aggregated = {
        "total_parallel_time_seconds": round(total_parallel_time, 2),
        "sessions": {}
    }

    for s in SESSIONS:
        rep_p = Path(s["report_file"])
        if rep_p.exists():
            with open(rep_p, "r", encoding="utf-8") as f:
                data = json.load(f)
                aggregated["sessions"][s["name"]] = data
        else:
            print(f"[!] Warning: Report file missing for {s['name']}")

    summary_file = Path(r"c:\Users\KISHORE S\Desktop\pulled_tmi\benchmark_parallel_4_summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(aggregated, f, ensure_ascii=False, indent=2)

    print(f"Aggregated summary written to: {summary_file}")

if __name__ == "__main__":
    main()
