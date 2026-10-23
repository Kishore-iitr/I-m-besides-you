"""
Comprehensive Step-by-Step TMI Pipeline Execution with Complete Transparency
Runs on a single real session from Dataset A (ses_20260701-053005-MSI).
Logs every step from raw event ingestion, pattern discovery, Puter prompt, Puter response,
boundary snapping, deliverable generation, and post-hoc evaluation.
"""

import os
import re
import sys
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Setup paths
SESSION_DIR = Path(r"G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_a\ses_20260701-053005-MSI")
OUTPUT_FILE = Path(r"c:\Users\KISHORE S\Desktop\pulled_tmi\segments.jsonl")

PUTER_TOKEN = os.environ.get(
    "PUTER_AUTH_TOKEN",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6InYyIn0.eyJ0IjoiYXUiLCJ2IjoiMiIsInV1IjoiZ0dXcTBPVE1TdEdSWkZWK2RQZEFWZz09IiwiYXUiOiJKaFNmQzRNRVVpaTVsWGN0cmM5QkRnPT0iLCJzdSI6ImhUS1diTTNnVCtxMHBvVHZpT2JsMUE9PSIsImFpIjoiZ0dXcTBPVE1TdEdSWkZWK2RQZEFWZz09IiwiaWF0IjoxNzkyNTY1OTE4fQ.XrFC2-zDsTcgmO7ioM3kXqu89Wqf48fkFaxZZQs1k1U"
)
PUTER_MODEL = os.environ.get("PUTER_MODEL", "openrouter:minimax/minimax-m3.1-flash:free")
PUTER_URL = "https://api.puter.com/drivers/call"

THREE_PART_REGEX = re.compile(r'\b([A-Z]{2,6})[-_](\d{4,8})[-_](\d{2,4})\b')
BLOCKED_APPS = {"procmine-desktop-agent.exe", "procmine-desktop-agent", "omapsvcbroker.exe"}
IGNORE_IDENTIFIERS = {"LAPTOP", "MSI", "CHUNK", "EVT", "MONITOR", "SESSION", "PROCMINE"}


def clean_iso(ts: str) -> str:
    if not ts: return ""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return ts.split(".")[0] + "Z" if "." in ts else ts


def to_epoch(ts: Optional[str]) -> float:
    if not ts: return 0.0
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.timestamp()
    except Exception:
        return 0.0


def main():
    print("=" * 80)
    print("STEP-BY-STEP VERIFIED EXECUTION: TASK MODEL INDUCTION PIPELINE")
    print(f"Session Directory: {SESSION_DIR}")
    print(f"Deliverable Path:  {OUTPUT_FILE}")
    print(f"LLM Provider:      Puter.js Driver API ({PUTER_MODEL})")
    print("=" * 80)

    # ---------------------------------------------------------
    # PHASE 1: RAW INGESTION OF OPERATION LOGS
    # ---------------------------------------------------------
    print("\n" + "#" * 80)
    print("PHASE 1: INGESTION OF RAW OPERATION LOGS (events.jsonl)")
    print("#" * 80)

    chunk_dirs = sorted([p for p in SESSION_DIR.iterdir() if p.is_dir() and "chunk_" in p.name])
    print(f"[Phase 1.1] Discovered {len(chunk_dirs)} recording chunk(s): {[c.name for c in chunk_dirs]}")

    raw_events = []
    for cdir in chunk_dirs:
        ev_file = cdir / "events.jsonl"
        print(f"[Phase 1.2] Reading raw event stream from: {ev_file}")
        with open(ev_file, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    ev = json.loads(line)
                    ev["_source_chunk"] = cdir.name
                    ev["_line_no"] = line_no
                    raw_events.append(ev)

    raw_events.sort(key=lambda x: x.get("timestamp_ms", 0))
    print(f"[Phase 1.3] Total raw events loaded into memory: {len(raw_events)}")

    # Show first 3 raw events
    print("\n--- SAMPLE RAW EVENTS AS INGESTED ---")
    for i, ev in enumerate(raw_events[:3]):
        ctx = ev.get("context", {}) or {}
        act = ctx.get("active_app", {}) or {}
        print(f"Event #{i+1} [Line {ev['_line_no']}] | Type: {ev.get('event_type'):<18} | Time: {ev.get('timestamp_iso')} | App: {act.get('app_name')} | Title: {act.get('window_title')}")

    # Filtering agent recorder noise
    clean_events = []
    noise_count = 0
    for ev in raw_events:
        if ev.get("layer") == "SYSTEM":
            continue
        ctx = ev.get("context", {}) or {}
        act = ctx.get("active_app", {}) or {}
        pname = (act.get("process_name") or "").lower()
        aname = (act.get("app_name") or "").lower()
        if pname in BLOCKED_APPS or aname in BLOCKED_APPS:
            noise_count += 1
            continue
        clean_events.append(ev)

    print(f"\n[Phase 1.4] Filtered out {noise_count} agent noise events. Remaining user interaction events: {len(clean_events)}")
    print(f"Time span: {clean_events[0]['timestamp_iso']} -> {clean_events[-1]['timestamp_iso']}")

    # ---------------------------------------------------------
    # PHASE 2: DISCOVERY OF CASE IDENTIFIERS FROM TRACE
    # ---------------------------------------------------------
    print("\n" + "#" * 80)
    print("PHASE 2: TRACE DISCOVERY & CASE SEQUENCE IDENTIFICATION (ZERO LEAKAGE)")
    print("#" * 80)

    # Detect batch pattern without hardcoding
    batch_counts = Counter()
    for ev in clean_events:
        text = " ".join([
            ev.get("context", {}).get("active_app", {}).get("window_title", ""),
            str(ev.get("context", {}).get("extracted_text", "")),
            str(ev.get("payload", {}))
        ])
        for m in THREE_PART_REGEX.finditer(text):
            batch_id = m.group(2)
            batch_counts[batch_id] += 1

    print(f"[Phase 2.1] Discovered 3-part identifier batches: {dict(batch_counts)}")
    dominant_batch = batch_counts.most_common(1)[0][0]
    print(f"[Phase 2.2] Identified dominant session batch ID: '{dominant_batch}' ({batch_counts[dominant_batch]} occurrences)")

    # Identify individual case executions by chronological first appearance
    case_first_idx = {}
    case_last_idx = {}

    for i, ev in enumerate(clean_events):
        text = " ".join([
            ev.get("context", {}).get("active_app", {}).get("window_title", ""),
            str(ev.get("context", {}).get("extracted_text", "")),
            str(ev.get("payload", {}))
        ])
        m = re.search(rf'\b([A-Z]{{2,6}})[-_]{dominant_batch}[-_](\d{{2,4}})\b', text)
        if m:
            cid = f"{m.group(1)}-{dominant_batch}-{m.group(2)}"
            if cid not in case_first_idx:
                case_first_idx[cid] = i
            case_last_idx[cid] = i

    ordered_cases = sorted(case_first_idx.keys(), key=lambda c: case_first_idx[c])
    print(f"\n[Phase 2.3] Discovered {len(ordered_cases)} distinct case executions in chronological order:")
    for idx, cid in enumerate(ordered_cases, 1):
        first_ev = clean_events[case_first_idx[cid]]
        app = first_ev.get("context", {}).get("active_app", {}).get("app_name")
        print(f"  {idx:02d}. Case: {cid:<15} | First Seen: {first_ev['timestamp_iso']} | App: {app}")

    # ---------------------------------------------------------
    # PHASE 3: EXTRACTION OF OBSERVED UI CONTEXT FOR EACH PROCESS
    # ---------------------------------------------------------
    print("\n" + "#" * 80)
    print("PHASE 3: DYNAMIC EXTRACTION OF OBSERVED UI CONTEXT (ZERO LEAKAGE)")
    print("#" * 80)

    # Snap boundaries for each case
    start_indices = []
    start_boundaries = []
    for idx, cid in enumerate(ordered_cases):
        ev_i = case_first_idx[cid]
        fev = clean_events[ev_i]
        best_i = ev_i
        prev_bound_idx = case_first_idx[ordered_cases[idx - 1]] if idx > 0 else 0

        for b_i in range(ev_i, max(0, ev_i - 50), -1):
            bev = clean_events[b_i]
            if idx > 0 and b_i <= prev_bound_idx:
                break
            if (fev["timestamp_ms"] - bev["timestamp_ms"]) > 6000:
                break
            if bev.get("event_type") in ("app_switch", "browser_navigation"):
                best_i = b_i

        start_indices.append(best_i)
        start_boundaries.append(clean_iso(clean_events[best_i]["timestamp_iso"]))

    # Detect final execution end
    last_cid = ordered_cases[-1]
    last_case_i = case_last_idx[last_cid]
    end_last_i = last_case_i
    for f_i in range(last_case_i, len(clean_events)):
        fev = clean_events[f_i]
        if fev["timestamp_ms"] - clean_events[end_last_i]["timestamp_ms"] > 15000:
            break
        end_last_i = f_i
    last_boundary = clean_iso(clean_events[end_last_i]["timestamp_iso"])

    # Extract UI evidence per prefix dynamically from raw events (zero leakage)
    GENERIC_IGNORE = {
        'ダッシュボード', '2026年度', 'HR人事給与システム', '受発注在庫管理システム',
        '財務会計システム', 'Google Chrome', 'Notepad', 'Microsoft Word', 'Excel',
        'm1_reference', 'Task Switching', 'Restore pages?', 'Address and search bar'
    }

    prefix_metadata = {}
    for idx in range(len(ordered_cases)):
        cid = ordered_cases[idx]
        pfx = cid.split("-")[0].upper()
        st_i = start_indices[idx]
        et_i = start_indices[idx + 1] if idx + 1 < len(start_indices) else end_last_i + 1

        if pfx not in prefix_metadata:
            prefix_metadata[pfx] = {
                "apps": Counter(),
                "portals": Counter(),
                "url_paths": Counter(),
                "keywords": Counter()
            }

        meta = prefix_metadata[pfx]
        for ev_i in range(st_i, min(et_i, len(clean_events))):
            ev = clean_events[ev_i]
            ctx = ev.get("context", {}) or {}
            act = ctx.get("active_app", {}) or {}
            aname = act.get("app_name")
            wtitle = act.get("window_title") or ""
            if aname and aname != "unknown":
                meta["apps"][aname] += 1
            if "財務会計" in wtitle:
                meta["portals"]["財務会計システム (Financial Accounting)"] += 1
            elif "人事給与" in wtitle:
                meta["portals"]["HR人事給与システム (HR Management)"] += 1
            elif "受発注在庫" in wtitle:
                meta["portals"]["受発注在庫管理システム (Order & Inventory)"] += 1

            ext = ctx.get("extracted_text")
            s = ""
            if ext:
                s = ext.get("text") if isinstance(ext, dict) else str(ext)
            full_text = f"{wtitle}\n{s}"

            # Extract active web paths from trace
            for u in re.findall(r'/#/([a-zA-Z0-9_\-]+)', full_text):
                if u not in ('dashboard', 'login'):
                    meta["url_paths"][u] += 2

            # Extract distinct Japanese UI action terms
            for line in full_text.split("\n"):
                line = line.strip()
                if 2 <= len(line) <= 25 and line not in GENERIC_IGNORE and not line.startswith(('http', '127.')):
                    if any(ord(c) > 127 for c in line):
                        meta["keywords"][line] += 1

    formatted_meta = {}
    for pfx, d in prefix_metadata.items():
        top_apps = [app for app, _ in d["apps"].most_common(2)]
        top_portal = d["portals"].most_common(1)[0][0] if d["portals"] else "Internal Web Portal"
        top_urls = [f"url: {u}" for u, _ in d["url_paths"].most_common(2)]
        top_kw = [k for k, _ in d["keywords"].most_common(3) if not any(u in k for u in ['url:'])]
        context_items = top_urls + top_kw
        formatted_meta[pfx] = {
            "apps": top_apps,
            "portal": top_portal,
            "ui_context": ", ".join(context_items[:4]) if context_items else "internal processing"
        }
        print(f"[Prefix: {pfx:<4}] Portal: {top_portal:<42} | Context: {formatted_meta[pfx]['ui_context']}")

    # ---------------------------------------------------------
    # PHASE 4: PUTER LLM INVOCATION & OBSERVABLE RAW LOGS
    # ---------------------------------------------------------
    print("\n" + "#" * 80)
    print("PHASE 4: PUTER LLM INVOCATION (LATENT TASK INDUCTION)")
    print("#" * 80)

    compact_threads = []
    for pfx in sorted(formatted_meta.keys()):
        meta = formatted_meta[pfx]
        compact_threads.append({
            "thread_id": pfx,
            "portal": meta["portal"],
            "ui_context": meta["ui_context"]
        })

    prompt = f"""Assign a canonical generic English snake_case business process label to each observed workflow thread:

{json.dumps(compact_threads, ensure_ascii=False, indent=2)}

Output strictly valid JSON with no extra commentary:
{{
  "labels": {{
    "INV": "canonical_snake_case_name"
  }}
}}"""

    print(">>> EXACT PROMPT SENT TO PUTER LLM >>>")
    print(prompt)
    print("<<< END PROMPT <<<\n")

    print(f"Connecting to Puter Driver API ({PUTER_URL})...")
    print(f"Model: {PUTER_MODEL}")

    import urllib.request
    payload = {
        "interface": "puter-chat-completion",
        "driver": "ai-chat",
        "test_mode": False,
        "method": "complete",
        "args": {
            "messages": [
                {"role": "system", "content": "You are an enterprise business process analyst. Return only JSON."},
                {"role": "user", "content": prompt}
            ],
            "model": PUTER_MODEL,
            "stream": False,
            "temperature": 0.1
        }
    }

    req = urllib.request.Request(
        PUTER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {PUTER_TOKEN}"},
        method="POST"
    )

    t0 = time.time()
    raw_res = ""
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=90) as res:
                raw_res = res.read().decode("utf-8")
                break
        except Exception as e:
            if attempt == 0:
                print(f"[Warning] Puter API timeout/error ({e}), retrying once...")
                time.sleep(2)
            else:
                raise e

    elapsed = time.time() - t0
    res_data = json.loads(raw_res)
    raw_message = res_data.get("result", {}).get("message", {}).get("content", "")

    print(f">>> RAW RESPONSE RECEIVED FROM PUTER IN {elapsed:.2f}s >>>")
    print(raw_message)
    print("<<< END RAW RESPONSE <<<\n")

    # Extract JSON
    cleaned = raw_message.strip()
    cleaned = re.sub(r'<think>[\s\S]*?</think>', '', cleaned).strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()

    first_curly = cleaned.find('{')
    last_curly = cleaned.rfind('}')
    label_map = json.loads(cleaned[first_curly:last_curly+1]).get("labels", {})

    print("[Phase 4.1] Extracted Process Label Mapping from Puter:")
    for k, v in label_map.items():
        print(f"  Thread '{k}' -> '{v}'")

    # ---------------------------------------------------------
    # PHASE 5: SEGMENTS GENERATION (segments.jsonl)
    # ---------------------------------------------------------
    print("\n" + "#" * 80)
    print("PHASE 5: DELIVERABLE GENERATION (segments.jsonl)")
    print("#" * 80)

    session_id = SESSION_DIR.name
    segments = []
    for i in range(len(ordered_cases)):
        cid = ordered_cases[i]
        pfx = cid.split("-")[0].upper()
        lbl = label_map.get(pfx, f"{pfx.lower()}_processing")
        st = start_boundaries[i]
        et = start_boundaries[i + 1] if i + 1 < len(start_boundaries) else last_boundary
        segments.append({
            "session_id": session_id,
            "start": st,
            "end": et,
            "label": lbl,
            "case_id": cid
        })

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for s in segments:
            f.write(json.dumps({
                "session_id": s["session_id"],
                "start": s["start"],
                "end": s["end"],
                "label": s["label"]
            }, ensure_ascii=False) + "\n")

    print(f"[Phase 5.1] Generated {len(segments)} segments written to: {OUTPUT_FILE}")
    print("\n--- FIRST 5 GENERATED SEGMENTS ---")
    for s in segments[:5]:
        print(f"  {s['start']} -> {s['end']} | Label: {s['label']:<32} | Case: {s['case_id']}")

    # ---------------------------------------------------------
    # PHASE 6: POST-HOC GROUND TRUTH EVALUATION (STRICTLY ISOLATED)
    # ---------------------------------------------------------
    print("\n" + "#" * 80)
    print("PHASE 6: POST-HOC EVALUATION AGAINST GROUND TRUTH (gt_manifest.json)")
    print("#" * 80)

    gt_manifest_file = SESSION_DIR / "gt_manifest.json"
    if not gt_manifest_file.exists():
        print("No ground truth manifest found.")
        return

    print(f"Reading ground truth manifest strictly post-hoc: {gt_manifest_file}")
    with open(gt_manifest_file, "r", encoding="utf-8") as f:
        gt_manifest = json.load(f)

    gt_executions = []
    for proc in gt_manifest.get("processes", []):
        code = proc.get("code")
        family = proc.get("family_name")
        for exec_item in proc.get("executions", []):
            gt_executions.append({
                "code": code,
                "family_name": family,
                "case_id": exec_item.get("case_id"),
                "start_ts": exec_item.get("start_ts"),
                "end_ts": exec_item.get("end_ts"),
                "start_sec": to_epoch(exec_item.get("start_ts")),
                "end_sec": to_epoch(exec_item.get("end_ts")),
            })
    gt_executions.sort(key=lambda x: x["start_sec"])

    for idx in range(len(gt_executions)):
        if not gt_executions[idx]["end_sec"] or gt_executions[idx]["end_sec"] == 0.0:
            if idx + 1 < len(gt_executions):
                gt_executions[idx]["end_sec"] = gt_executions[idx + 1]["start_sec"]

    preds = []
    for p in segments:
        preds.append({
            **p,
            "start_sec": to_epoch(p["start"]),
            "end_sec": to_epoch(p["end"]),
        })
    preds.sort(key=lambda x: x["start_sec"])

    print(f"Total Predicted Segments:   {len(preds)}")
    print(f"Total Ground Truth Execs:   {len(gt_executions)}")

    print("\nBoundary Evaluation Metrics:")
    for tol in [2, 5, 10, 30]:
        tp = 0
        matched_gt = set()
        for p in preds:
            for idx, gt in enumerate(gt_executions):
                if idx in matched_gt: continue
                s_diff = abs(p["start_sec"] - gt["start_sec"])
                e_diff = abs(p["end_sec"] - gt["end_sec"])
                if s_diff <= tol and e_diff <= tol:
                    tp += 1
                    matched_gt.add(idx)
                    break
        prec = tp / len(preds)
        rec = tp / len(gt_executions)
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        print(f"  Tolerance <= {tol:>2}s: TP={tp:>2}/{len(gt_executions)} | Precision={prec*100:5.1f}% | Recall={rec*100:5.1f}% | F1={f1*100:5.1f}%")

    print("\nPredicted Label to Ground Truth Alignment:")
    label_mapping = {}
    for p in preds:
        lbl = p["label"]
        cid = p.get("case_id")
        for gt in gt_executions:
            if (cid and gt["case_id"] == cid) or (abs(p["start_sec"] - gt["start_sec"]) <= 15):
                if lbl not in label_mapping:
                    label_mapping[lbl] = {}
                gt_key = f"{gt['code']} ({gt['family_name']})"
                label_mapping[lbl][gt_key] = label_mapping[lbl].get(gt_key, 0) + 1

    for lbl, counts in sorted(label_mapping.items()):
        best_gt = max(counts.items(), key=lambda x: x[1])
        print(f"  Predicted '{lbl}' -> {best_gt[0]} ({best_gt[1]} matches)")


if __name__ == "__main__":
    main()
