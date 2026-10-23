import sys
import os
import time
import subprocess
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PYTHON_EXE = r"C:\Users\KISHORE S\anaconda3\python.exe"
SCRIPT_PATH = r"c:\Users\KISHORE S\Desktop\pulled_tmi\run_pipeline_dataset_b.py"
DATASET_B_DIR = Path(r"G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_b")
CHECKPOINT_DIR = Path(r"c:\Users\KISHORE S\Desktop\pulled_tmi\checkpoints")
LOGS_DIR = Path(r"c:\Users\KISHORE S\Desktop\pulled_tmi\logs")
MASTER_SEGMENTS_FILE = Path(r"c:\Users\KISHORE S\Desktop\pulled_tmi\segments.jsonl")
BACKUP_SEGMENTS_FILE = Path(r"c:\Users\KISHORE S\Desktop\pulled_tmi\segments_dataset_b.jsonl")
PROFILING_SUMMARY_FILE = Path(r"c:\Users\KISHORE S\Desktop\pulled_tmi\dataset_b_automation_profiling.json")

CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Parallel worker limit
MAX_CONCURRENT_WORKERS = 4


def get_dataset_b_sessions():
    sessions = sorted([d for d in DATASET_B_DIR.iterdir() if d.is_dir()])
    return sessions


def is_session_completed(session_id: str) -> bool:
    ckpt_file = CHECKPOINT_DIR / f"checkpoint_{session_id}.json"
    if ckpt_file.exists():
        try:
            with open(ckpt_file, "r", encoding="utf-8") as f:
                d = json.load(f)
            if d.get("status") == "completed" and d.get("segments"):
                return True
        except Exception:
            return False
    return False


def main():
    print("=" * 90)
    print("DATASET B COMPLETE PIPELINE ORCHESTRATOR WITH CHECKPOINTING & PARALLEL WORKERS")
    print(f"Dataset B Directory:    {DATASET_B_DIR}")
    print(f"Checkpoints Directory:  {CHECKPOINT_DIR}")
    print(f"Max Concurrent Workers: {MAX_CONCURRENT_WORKERS}")
    print(f"Master Deliverable:     {MASTER_SEGMENTS_FILE}")
    print("=" * 90)

    sessions = get_dataset_b_sessions()
    print(f"\nDiscovered {len(sessions)} total sessions in Dataset B:")
    for idx, s in enumerate(sessions, 1):
        status = "COMPLETED" if is_session_completed(s.name) else "PENDING"
        print(f"  {idx:02d}. {s.name:<36} | Status: {status}")

    t0 = time.time()
    pending = list(sessions)
    active_procs = []
    completed_reports = {}

    while pending or active_procs:
        # Launch new workers if slots available
        while pending and len(active_procs) < MAX_CONCURRENT_WORKERS:
            s = pending.pop(0)
            sid = s.name
            if is_session_completed(sid):
                elapsed = time.time() - t0
                print(f"[+] [{elapsed:6.1f}s] [Checkpoint Cache] Session '{sid}' already verified completed.")
                ckpt_p = CHECKPOINT_DIR / f"checkpoint_{sid}.json"
                with open(ckpt_p, "r", encoding="utf-8") as f:
                    completed_reports[sid] = json.load(f)
                continue

            log_file = LOGS_DIR / f"run_{sid}.log"
            log_fp = open(log_file, "w", encoding="utf-8")
            cmd = [
                PYTHON_EXE,
                "-u",
                SCRIPT_PATH,
                "--session_dir", str(s),
                "--checkpoint_dir", str(CHECKPOINT_DIR),
                "--output_file", str(CHECKPOINT_DIR / f"segments_{sid}.jsonl"),
                "--report_file", str(CHECKPOINT_DIR / f"report_{sid}.json")
            ]
            p = subprocess.Popen(cmd, stdout=log_fp, stderr=subprocess.STDOUT)
            active_procs.append({
                "session": s,
                "session_id": sid,
                "proc": p,
                "log_fp": log_fp,
                "log_file": log_file,
                "launch_time": time.time()
            })
            print(f"[*] Started worker for '{sid}' (PID {p.pid}). Slot {len(active_procs)}/{MAX_CONCURRENT_WORKERS}")

        # Monitor active workers
        time.sleep(3)
        still_active = []
        for worker in active_procs:
            p = worker["proc"]
            ret = p.poll()
            if ret is None:
                still_active.append(worker)
            else:
                worker["log_fp"].close()
                worker_dur = time.time() - worker["launch_time"]
                elapsed = time.time() - t0
                sid = worker["session_id"]
                if ret == 0 and is_session_completed(sid):
                    print(f"[+] [{elapsed:6.1f}s] Worker for '{sid}' (PID {p.pid}) COMPLETED successfully in {worker_dur:.1f}s.")
                    ckpt_p = CHECKPOINT_DIR / f"checkpoint_{sid}.json"
                    with open(ckpt_p, "r", encoding="utf-8") as f:
                        completed_reports[sid] = json.load(f)
                else:
                    print(f"[!] [{elapsed:6.1f}s] Worker for '{sid}' (PID {p.pid}) FAILED with exit code {ret}. See {worker['log_file']}")
        active_procs = still_active

    total_parallel_time = time.time() - t0
    print("\n" + "=" * 90)
    print(f"ALL {len(sessions)} DATASET B SESSIONS PROCESSED IN {total_parallel_time:.2f}s ({total_parallel_time/60:.2f} min)")
    print("=" * 90)

    # -------------------------------------------------------------------------
    # CONSOLIDATE DELIVERABLE: segments.jsonl
    # -------------------------------------------------------------------------
    all_segments = []
    for s in sessions:
        sid = s.name
        rep = completed_reports.get(sid)
        if rep and rep.get("segments"):
            for seg in rep["segments"]:
                all_segments.append(seg)

    # Sort all segments chronologically by start timestamp
    all_segments.sort(key=lambda x: x.get("start", ""))

    with open(MASTER_SEGMENTS_FILE, "w", encoding="utf-8") as mf:
        for seg in all_segments:
            line_obj = {
                "session_id": seg["session_id"],
                "start": seg["start"],
                "end": seg["end"],
                "label": seg["label"]
            }
            mf.write(json.dumps(line_obj, ensure_ascii=False) + "\n")

    # Also save backup copy
    with open(BACKUP_SEGMENTS_FILE, "w", encoding="utf-8") as bf:
        for seg in all_segments:
            line_obj = {
                "session_id": seg["session_id"],
                "start": seg["start"],
                "end": seg["end"],
                "label": seg["label"]
            }
            bf.write(json.dumps(line_obj, ensure_ascii=False) + "\n")

    print(f"\n[Deliverable Written] Successfully generated master deliverable with {len(all_segments)} segments:")
    print(f"  Primary: {MASTER_SEGMENTS_FILE}")
    print(f"  Backup:  {BACKUP_SEGMENTS_FILE}")

    # -------------------------------------------------------------------------
    # COMPILE COMPREHENSIVE AUTOMATION PROFILING TELEMETRY (FOR STEP 2)
    # -------------------------------------------------------------------------
    process_stats = defaultdict(lambda: {
        "execution_count": 0,
        "total_duration_seconds": 0.0,
        "durations": [],
        "operators": Counter(),
        "sessions": Counter(),
        "total_keystrokes": 0,
        "total_clicks": 0,
        "total_clipboard_ops": 0,
        "total_app_switches": 0,
        "cross_system_transfers_count": 0,
        "active_applications": Counter(),
        "web_routes": Counter(),
        "automation_suitability_scores": []
    })

    total_work_seconds = sum(s.get("duration_seconds", 0) for s in all_segments)

    for s in all_segments:
        lbl = s["label"]
        dur = s.get("duration_seconds", 0)
        op = s.get("operator", "unknown")
        sid = s.get("session_id", "unknown")
        telem = s.get("automation_telemetry") or {}

        pstat = process_stats[lbl]
        pstat["execution_count"] += 1
        pstat["total_duration_seconds"] += dur
        pstat["durations"].append(dur)
        pstat["operators"][op] += 1
        pstat["sessions"][sid] += 1
        pstat["total_keystrokes"] += telem.get("keystrokes_count", 0)
        pstat["total_clicks"] += telem.get("clicks_count", 0)
        pstat["total_clipboard_ops"] += telem.get("clipboard_operations", 0)
        pstat["total_app_switches"] += telem.get("app_switches_count", 0)
        if telem.get("cross_system_transfer"):
            pstat["cross_system_transfers_count"] += 1
        for app in telem.get("active_applications", []):
            pstat["active_applications"][app] += 1
        for r in telem.get("web_routes", []):
            pstat["web_routes"][r] += 1
        pstat["automation_suitability_scores"].append(telem.get("automation_suitability_score", 50.0))

    summary_by_process = {}
    for lbl, st in sorted(process_stats.items(), key=lambda x: x[1]["total_duration_seconds"], reverse=True):
        cnt = st["execution_count"]
        tot_dur = st["total_duration_seconds"]
        mean_dur = tot_dur / cnt if cnt > 0 else 0
        min_dur = min(st["durations"]) if st["durations"] else 0
        max_dur = max(st["durations"]) if st["durations"] else 0
        pct_time = (tot_dur / total_work_seconds * 100) if total_work_seconds > 0 else 0
        mean_suitability = sum(st["automation_suitability_scores"]) / cnt if cnt > 0 else 0
        cross_sys_pct = (st["cross_system_transfers_count"] / cnt * 100) if cnt > 0 else 0

        # Automation Priority Score (Composite of Volume x Time x Suitability x Cross-app Friction)
        priority_score = round((tot_dur / 60.0) * (mean_suitability / 100.0) * (1.0 + cross_sys_pct / 100.0), 2)

        summary_by_process[lbl] = {
            "execution_count": cnt,
            "total_duration_seconds": round(tot_dur, 2),
            "total_duration_minutes": round(tot_dur / 60.0, 2),
            "percentage_of_total_work_time": round(pct_time, 2),
            "mean_duration_seconds": round(mean_dur, 2),
            "min_duration_seconds": round(min_dur, 2),
            "max_duration_seconds": round(max_dur, 2),
            "operators_involved": dict(st["operators"]),
            "sessions_involved": len(st["sessions"]),
            "average_keystrokes_per_case": round(st["total_keystrokes"] / cnt, 1) if cnt > 0 else 0,
            "average_clicks_per_case": round(st["total_clicks"] / cnt, 1) if cnt > 0 else 0,
            "average_clipboard_ops_per_case": round(st["total_clipboard_ops"] / cnt, 1) if cnt > 0 else 0,
            "cross_system_transfer_rate_pct": round(cross_sys_pct, 1),
            "mean_automation_suitability_index": round(mean_suitability, 1),
            "automation_priority_score": priority_score,
            "frequent_applications": [k for k, _ in st["active_applications"].most_common(4)],
            "frequent_web_routes": [k for k, _ in st["web_routes"].most_common(4)]
        }

    profiling_deliverable = {
        "dataset": "dataset_b",
        "total_sessions": len(sessions),
        "total_segments_recovered": len(all_segments),
        "total_work_duration_seconds": round(total_work_seconds, 2),
        "total_work_duration_hours": round(total_work_seconds / 3600.0, 2),
        "total_parallel_wall_time_seconds": round(total_parallel_time, 2),
        "processes_ranked_by_priority": sorted(
            summary_by_process.items(),
            key=lambda x: x[1]["automation_priority_score"],
            reverse=True
        ),
        "process_summary": summary_by_process,
        "all_segments_telemetry": all_segments
    }

    with open(PROFILING_SUMMARY_FILE, "w", encoding="utf-8") as pf:
        json.dump(profiling_deliverable, pf, ensure_ascii=False, indent=2)

    print(f"\n[Automation Profiling Saved] Step 2 candidate discovery data saved to: {PROFILING_SUMMARY_FILE}")
    print("\n" + "=" * 90)
    print("TOP AUTOMATION CANDIDATE PREVIEW (FROM STEP 1 OUTPUT)")
    print("=" * 90)
    print(f"{'Process Label':<32} {'Count':>6} {'Total Time':>12} {'% Work':>8} {'Cross-Sys %':>12} {'Priority Score':>15}")
    print("-" * 90)
    for lbl, data in profiling_deliverable["processes_ranked_by_priority"][:8]:
        print(f"{lbl:<32} {data['execution_count']:>6} {data['total_duration_minutes']:>9.1f}m {data['percentage_of_total_work_time']:>7.1f}% {data['cross_system_transfer_rate_pct']:>11.1f}% {data['automation_priority_score']:>15.2f}")
    print("=" * 90)


if __name__ == "__main__":
    main()
