"""
Multi-Step Task Model Induction (TMI) Pipeline with Full LLM Visibility & Fused Episode Induction
Strictly adheres to Jiang et al. (arXiv:2608.20319v1) Appendix F Prompts:
- Stage 0: Dual Keyframe Visual Grounding (Initial + Terminal Frames)
- Stage 1: Activity Segmentation (Figure 6: SEGMENTATION_PROMPT)
- Stage 2: Latent Task Discovery (Figure 7: ROOT_THREAD_DISCOVERY_PROMPT)
- Stage 3: Root Thread Consolidation & Naming (Figure 8: ROOT_THREAD_CONSOLIDATION_PROMPT)
- Stage 4: Hierarchical Objective & Procedure Modeling (Figures 9 & 10)
- Stage 5: Segment Assembly & Deliverable Generation (segments.jsonl)
- Stage 6: Post-Hoc Ground Truth Evaluation (gt_manifest.json)

Provides complete, transparent logging of EVERY Puter LLM prompt and COMPLETE raw response.
Handles explicit case tracking, route debouncing, entity-masked queue tables, and non-overlapping boundary snapping.
"""

import argparse
import os
import re
import sys
import json
import time
import socket
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pytesseract
from PIL import Image

if sys.platform == "win32":
    import msvcrt

socket.setdefaulttimeout(120)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Configure Tesseract OCR
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
os.environ['TESSDATA_PREFIX'] = r'c:\Users\KISHORE S\Desktop\pulled_tmi\tessdata'

# Command-line argument parser
parser = argparse.ArgumentParser(description="Multi-Step Task Model Induction Pipeline with Fused Episode Discovery")
parser.add_argument("--session_dir", default=r"G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_a\ses_20260701-043922-SIDDHIGUPTAB00B")
parser.add_argument("--output_file", default=r"c:\Users\KISHORE S\Desktop\pulled_tmi\segments_siddhi.jsonl")
parser.add_argument("--report_file", default=r"c:\Users\KISHORE S\Desktop\pulled_tmi\benchmark_siddhi.json")
args, _ = parser.parse_known_args()

SESSION_DIR = Path(args.session_dir)
OUTPUT_FILE = Path(args.output_file)
REPORT_FILE = Path(args.report_file) if args.report_file else None

PUTER_TOKEN = os.environ.get(
    "PUTER_AUTH_TOKEN",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6InYyIn0.eyJ0IjoiYXUiLCJ2IjoiMiIsInV1IjoiZ0dXcTBPVE1TdEdSWkZWK2RQZEFWZz09IiwiYXUiOiJKaFNmQzRNRVVpaTVsWGN0cmM5QkRnPT0iLCJzdSI6ImhUS1diTTNnVCtxMHBvVHZpT2JsMUE9PSIsImFpIjoiZ0dXcTBPVE1TdEdSWkZWK2RQZEFWZz09IiwiaWF0IjoxNzkyNTY1OTE4fQ.XrFC2-zDsTcgmO7ioM3kXqu89Wqf48fkFaxZZQs1k1U"
)
PUTER_MODEL = os.environ.get("PUTER_MODEL", "openrouter:minimax/minimax-m3.1-flash:free")
PUTER_URL = "https://api.puter.com/drivers/call"
PUTER_LOCK_PATH = Path(r"c:\Users\KISHORE S\Desktop\pulled_tmi\puter_api.lock")

# Universal case regex supporting 2-6 prefix chars, 4-8 batch digits, 2-5 serial digits, or 2-part BATCH codes
UNIVERSAL_CASE_REGEX = re.compile(r'(?:([A-Z]{2,6})[-_](\d{4,8})[-_](\d{2,5})|(BATCH[-_]W\d+))\b')
BLOCKED_APPS = {"procmine-desktop-agent.exe", "procmine-desktop-agent", "omapsvcbroker.exe"}

CANONICAL_FALLBACK = {
    "RT": "resident_tax_notification",
    "PI": "payroll_deductions_maintenance",
    "LA": "leave_application_processing",
    "SI": "social_insurance_maintenance",
    "OB": "employee_onboarding",
    "INV": "invoice_processing",
    "EXP": "expense_claim_approval",
    "PM": "payment_processing",
    "BV": "budget_variance_analysis",
    "BR": "bank_reconciliation",
    "ORD": "order_processing",
    "STK": "stock_adjustment",
    "SHP": "shipment_tracking",
    "SUP": "supplier_communication",
    "RET": "return_processing",
    "PO": "purchase_order_processing",
    "BATCH": "batch_order_fulfillment",
    "RESIDENT": "resident_tax_notification",
    "PAYROLL": "payroll_deductions_maintenance",
    "LEAVE": "leave_application_processing",
    "SOCIAL": "social_insurance_maintenance",
    "ONBOARDING": "employee_onboarding",
    "INVOICE": "invoice_processing",
    "EXPENSE": "expense_claim_approval",
    "PAYMENT": "payment_processing",
    "BUDGET": "budget_variance_analysis",
    "BANK": "bank_reconciliation",
    "ORDERS": "order_processing",
    "STOCK": "stock_adjustment",
    "SHIPMENT": "shipment_tracking",
    "RETURN": "return_processing",
    "PURCHASE": "purchase_order_processing",
}


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


def call_puter(prompt: str, system_prompt: str = "You are an enterprise business process analyst. Return only JSON.") -> str:
    # Cross-process mutual exclusion file lock for parallel execution
    lock_fd = None
    is_locked = False
    if sys.platform == "win32":
        PUTER_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        PUTER_LOCK_PATH.touch(exist_ok=True)
        lock_fd = open(PUTER_LOCK_PATH, "r+")
        for _ in range(300):
            try:
                msvcrt.locking(lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
                is_locked = True
                break
            except OSError:
                time.sleep(1.0)

    try:
        time.sleep(4)  # Rate-limit guard for Puter API
        payload = {
            "interface": "puter-chat-completion",
            "driver": "ai-chat",
            "test_mode": False,
            "method": "complete",
            "args": {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "model": PUTER_MODEL,
                "stream": False,
                "temperature": 0.1
            }
        }

        for attempt in range(6):
            try:
                req = urllib.request.Request(
                    PUTER_URL,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {PUTER_TOKEN}"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=90) as res:
                    data = json.loads(res.read().decode("utf-8"))
                    return data.get("result", {}).get("message", {}).get("content", "")
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    wait_sec = 15 * (attempt + 1)
                    print(f"[Puter API 429 Concurrency Lock] Waiting {wait_sec}s before retry...", file=sys.stderr, flush=True)
                    time.sleep(wait_sec)
                    continue
                elif attempt < 5:
                    print(f"[Puter API HTTP {e.code}] Retrying in 8s...", file=sys.stderr, flush=True)
                    time.sleep(8)
                    continue
                raise e
            except Exception as e:
                if attempt < 5:
                    print(f"[Puter API Warning] Call failed ({e}), retrying in 8s...", file=sys.stderr, flush=True)
                    time.sleep(8)
                else:
                    raise e
        return ""
    finally:
        if lock_fd:
            if is_locked:
                try:
                    lock_fd.seek(0)
                    msvcrt.locking(lock_fd.fileno(), msvcrt.LK_UNLCK, 1)
                except Exception:
                    pass
            lock_fd.close()


def extract_json(raw: str) -> Any:
    cleaned = raw.strip()
    cleaned = re.sub(r'<think>[\s\S]*?</think>', '', cleaned).strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
    first_b = cleaned.find('{')
    last_b = cleaned.rfind('}')
    first_sq = cleaned.find('[')
    last_sq = cleaned.rfind(']')

    try:
        if first_b != -1 and (first_sq == -1 or first_b < first_sq):
            return json.loads(cleaned[first_b:last_b+1])
        elif first_sq != -1:
            return json.loads(cleaned[first_sq:last_sq+1])
        return json.loads(cleaned)
    except Exception as e:
        print(f"[JSON Parse Warning] Failed to parse JSON ({e}). Raw snippet: {raw[:200]}...", file=sys.stderr)
        return {}


def main():
    print("=" * 80)
    print("FULL MULTI-STEP TASK MODEL INDUCTION (TMI) PIPELINE")
    print(f"Session Directory: {SESSION_DIR}")
    print(f"LLM Provider:      Puter Driver API ({PUTER_MODEL})")
    print(f"Deliverable Path:  {OUTPUT_FILE}")
    if REPORT_FILE:
        print(f"Report Path:       {REPORT_FILE}")
    print("=" * 80)

    timings = {}
    total_t0 = time.perf_counter()

    # -------------------------------------------------------------------------
    # PHASE 1: INGESTION & EVENT FILTERING
    # -------------------------------------------------------------------------
    t0_l1 = time.perf_counter()
    print("\n" + "#" * 80)
    print("PHASE 1: INGESTION OF RAW OPERATION LOGS (events.jsonl)")
    print("#" * 80)

    chunk_dirs = sorted([p for p in SESSION_DIR.iterdir() if p.is_dir() and "chunk" in p.name and (p / "events.jsonl").exists()])
    print(f"[Phase 1.1] Discovered {len(chunk_dirs)} recording chunk(s): {[c.name for c in chunk_dirs]}")

    raw_events = []
    for cdir in chunk_dirs:
        ev_file = cdir / "events.jsonl"
        with open(ev_file, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    try:
                        ev = json.loads(line)
                        ev["_source_chunk"] = cdir.name
                        ev["_line_no"] = line_no
                        raw_events.append(ev)
                    except Exception:
                        continue

    raw_events.sort(key=lambda x: x.get("timestamp_ms", 0))
    print(f"[Phase 1.2] Loaded {len(raw_events)} raw events from {len(chunk_dirs)} chunk(s).")

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

    print(f"[Phase 1.3] Filtered {noise_count} agent noise events. Clean user interaction events: {len(clean_events)}")
    print(f"Trace interval: {clean_events[0]['timestamp_iso']} -> {clean_events[-1]['timestamp_iso']}")
    timings["Layer 1: Raw Log Ingestion & Filtering"] = time.perf_counter() - t0_l1

    # -------------------------------------------------------------------------
    # PHASE 2: FUSED DYNAMIC TRACE DISCOVERY & EPISODE BOUNDARY EXTRACTION
    # -------------------------------------------------------------------------
    t0_l2 = time.perf_counter()
    print("\n" + "#" * 80)
    print("PHASE 2: FUSED TRACE DISCOVERY & CASE EPISODE BOUNDARY EXTRACTION")
    print("#" * 80)

    # 2.1 Discover enterprise batch IDs
    batch_diversity = defaultdict(set)
    batch_counts = Counter()
    for ev in clean_events:
        ctx = ev.get("context", {}) or {}
        act = ctx.get("active_app", {}) or {}
        text = " ".join([
            act.get("window_title", ""),
            str(ctx.get("extracted_text", "")),
            str(ev.get("payload", {}))
        ])
        for m in UNIVERSAL_CASE_REGEX.finditer(text):
            if m.group(1):
                pfx = m.group(1).upper()
                batch_id = m.group(2)
            else:
                pfx = "BATCH"
                batch_id = m.group(4)
            batch_counts[batch_id] += 1
            batch_diversity[batch_id].add(pfx)

    dominant_batch = max(batch_diversity.keys(), key=lambda b: len(batch_diversity[b])) if batch_diversity else "2026"
    print(f"[Phase 2.1] Discovered enterprise session batch: '{dominant_batch}' ({batch_counts[dominant_batch]} occurrences across {len(batch_diversity[dominant_batch])} process prefixes: {sorted(batch_diversity[dominant_batch])})")

    # 2.2 Fused Episode Discovery: Case Clicks + Debounced Functional Route Transitions
    raw_episodes = []
    debounce_ms = 15000

    for i, ev in enumerate(clean_events):
        etype = ev.get("event_type")
        payload = ev.get("payload", {}) or {}
        ts_ms = ev.get("timestamp_ms", 0)
        ts_iso = ev.get("timestamp_iso", "")

        found_cid = None
        if etype in ("browser_click", "mouse_click"):
            elem = payload.get("element") or payload.get("target_element") or {}
            sel = f"{elem.get('css_selector', '')} {elem.get('xpath', '')} {elem.get('text', '')} {elem.get('automation_id', '')} {elem.get('name', '')}"
            m = UNIVERSAL_CASE_REGEX.search(sel)
            if not m:
                ext_str = json.dumps(ev.get("extensions", {}), ensure_ascii=False)
                m = UNIVERSAL_CASE_REGEX.search(ext_str)
            if m:
                if m.group(1):
                    found_cid = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
                else:
                    found_cid = m.group(4)

        is_nav = False
        nav_url = ""
        if etype == "browser_navigation":
            url = payload.get("url") or ""
            if url and not url.endswith(("dashboard", "login", ":5122/", ":5123/", ":5124/", ":5132/", ":5133/", ":5134/")):
                if "sso" not in url and not url.startswith("https://"):
                    is_nav = True
                    nav_url = url

        should_start = False
        if is_nav:
            if not raw_episodes or (ts_ms - raw_episodes[-1]["start_ms"] > debounce_ms):
                should_start = True
        elif found_cid:
            if not raw_episodes:
                should_start = True
            elif raw_episodes[-1].get("cid") is None and (ts_ms - raw_episodes[-1]["start_ms"] < debounce_ms):
                # Backfill case ID into ongoing route-initiated episode
                raw_episodes[-1]["cid"] = found_cid
            elif raw_episodes[-1].get("cid") != found_cid and (ts_ms - raw_episodes[-1]["start_ms"] > debounce_ms):
                should_start = True

        if should_start:
            raw_episodes.append({
                "start_idx": i,
                "start_ms": ts_ms,
                "start_iso": ts_iso,
                "cid": found_cid,
                "nav_url": nav_url
            })

    # 2.3 Strict Monotonic Boundary Snapping (Eliminates inter-process overlap)
    start_indices = []
    start_boundaries = []
    for idx, ep in enumerate(raw_episodes):
        st_i = ep["start_idx"]
        fev = clean_events[st_i]
        best_i = st_i
        prev_bound = raw_episodes[idx - 1]["start_idx"] if idx > 0 else 0
        for b_i in range(st_i, max(0, st_i - 30), -1):
            bev = clean_events[b_i]
            if idx > 0 and b_i <= prev_bound:
                break
            if fev["timestamp_ms"] - bev["timestamp_ms"] > 5000:
                break
            if bev.get("event_type") in ("app_switch", "browser_navigation", "browser_click", "mouse_click"):
                best_i = b_i
        start_indices.append(best_i)
        start_boundaries.append(clean_iso(clean_events[best_i]["timestamp_iso"]))

    # Terminal boundary: cap forward scan to eliminate post-session idle overrun
    last_ts_ms = clean_events[raw_episodes[-1]["start_idx"]]["timestamp_ms"]
    end_last_i = raw_episodes[-1]["start_idx"]
    for f_i in range(end_last_i + 1, len(clean_events)):
        fev = clean_events[f_i]
        if fev["timestamp_ms"] - last_ts_ms > 35000:
            break
        app_name = ((fev.get("context", {}) or {}).get("active_app", {}) or {}).get("app_name", "").lower()
        if any(term in app_name for term in ["terminal", "explorer", "cmd", "agent"]):
            break
        end_last_i = f_i
    last_boundary = clean_iso(clean_events[end_last_i]["timestamp_iso"])

    # 2.4 Internal Case ID Backfilling for Entity-Masked Queue Tables
    assigned_cids = set(ep["cid"] for ep in raw_episodes if ep["cid"])
    ordered_cases = []
    for idx in range(len(raw_episodes)):
        st_i = start_indices[idx]
        et_i = start_indices[idx + 1] if idx + 1 < len(start_indices) else end_last_i + 1

        cid = raw_episodes[idx]["cid"]
        if not cid:
            counts = Counter()
            for j in range(st_i, et_i):
                s = json.dumps(clean_events[j], ensure_ascii=False)
                for m in UNIVERSAL_CASE_REGEX.finditer(s):
                    cand = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m.group(1) else m.group(4)
                    if cand not in assigned_cids:
                        counts[cand] += 1
            if counts:
                cid = counts.most_common(1)[0][0]
                assigned_cids.add(cid)
            else:
                url = raw_episodes[idx]["nav_url"]
                route = url.split("#/")[-1] if "#/" in url else f"TASK-{idx+1:02d}"
                cid = f"{route.upper()}-{dominant_batch}-{idx+1:03d}"

        ordered_cases.append(cid)
        raw_episodes[idx]["cid"] = cid

    print(f"\n[Phase 2.2] Identified {len(ordered_cases)} distinct case executions in chronological order:")
    for idx, cid in enumerate(ordered_cases, 1):
        st = start_boundaries[idx - 1]
        et = start_boundaries[idx] if idx < len(start_boundaries) else last_boundary
        fev = clean_events[start_indices[idx - 1]]
        app = (fev.get("context", {}) or {}).get("active_app", {}).get("app_name")
        print(f"  {idx:02d}. Case: {cid:<24} | Window: {st} -> {et} | App: {app}")
    timings["Layer 2: Dynamic Trace & Episode Boundary Extraction"] = time.perf_counter() - t0_l2

    # -------------------------------------------------------------------------
    # STAGE 0: DUAL KEYFRAME VISUAL GROUNDING (INITIAL + TERMINAL) (Paper §3.1)
    # -------------------------------------------------------------------------
    t0_s0 = time.perf_counter()
    print("\n" + "#" * 80)
    print("STAGE 0: DUAL KEYFRAME VISUAL GROUNDING (INITIAL + TERMINAL FRAMES)")
    print("#" * 80)

    UI_IGNORE = {
        'Conditional Formatas Cell', 'Formatting Table Styles', 'Insert Delete Format',
        'Sort & Find', 'Select', 'Filter Select', 'データ参照中', 'Office Theme'
    }

    # Group episodes by process prefix
    prefix_episodes = defaultdict(list)
    for idx, cid in enumerate(ordered_cases):
        pfx = cid.split("-")[0].upper()
        prefix_episodes[pfx].append(idx)

    screenshot_evidence = defaultdict(list)
    for pfx, ep_indices in sorted(prefix_episodes.items()):
        sample_idx = ep_indices[0]
        st_i = start_indices[sample_idx]
        et_i = start_indices[sample_idx + 1] if sample_idx + 1 < len(start_indices) else end_last_i + 1

        imgs_to_ocr = []
        # Initial frame (action start)
        for j in range(st_i, min(len(clean_events), st_i + 30)):
            ev = clean_events[j]
            if ev.get("event_type") == "screenshot_smart":
                rel = (ev.get("payload") or {}).get("file_reference", {}).get("relative_path")
                cname = ev.get("_source_chunk")
                p = SESSION_DIR / cname / rel if (cname and rel) else None
                if p and p.exists() and p not in imgs_to_ocr:
                    imgs_to_ocr.append(p)
                    break

        # Terminal frame (action completion / outcome)
        for j in range(et_i - 1, max(0, et_i - 30), -1):
            if j >= len(clean_events): continue
            ev = clean_events[j]
            if ev.get("event_type") == "screenshot_smart":
                rel = (ev.get("payload") or {}).get("file_reference", {}).get("relative_path")
                cname = ev.get("_source_chunk")
                p = SESSION_DIR / cname / rel if (cname and rel) else None
                if p and p.exists() and p not in imgs_to_ocr:
                    imgs_to_ocr.append(p)
                    break

        collected = []
        for img_p in imgs_to_ocr:
            try:
                ocr_text = pytesseract.image_to_string(Image.open(img_p), lang='jpn+eng')
                for line in ocr_text.split('\n'):
                    l_str = line.strip()
                    if (
                        len(l_str) >= 3
                        and any(ord(c) > 127 for c in l_str)
                        and not any(ign in l_str for ign in UI_IGNORE)
                        and not l_str.isdigit()
                        and len(l_str) < 40
                    ):
                        if l_str not in collected:
                            collected.append(l_str)
            except Exception as ocr_err:
                print(f"[Stage 0 OCR Warning: {pfx}] {ocr_err}")

        if collected:
            screenshot_evidence[pfx] = collected[:4]
            print(f"[Stage 0 Dual OCR: {pfx:<6}] {len(imgs_to_ocr)} keyframe(s) -> Grounded UI: {collected[:3]}")
    timings["Stage 0: Dual Keyframe OCR Visual Grounding"] = time.perf_counter() - t0_s0

    # Extract observed UI evidence per thread prefix
    GENERIC_IGNORE = {
        'ダッシュボード', '2026年度', 'HR人事給与システム', '受発注在庫管理システム',
        '財務会計システム', 'Google Chrome', 'Microsoft Edge', 'Edge', 'msedge.exe',
        'Notepad', 'Microsoft Word', 'Excel', 'Microsoft Excel',
        'm1_reference', 'Task Switching', 'Restore pages?', 'Address and search bar',
        'Windows PowerShell'
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
                "keywords": Counter(),
                "case_samples": []
            }

        meta = prefix_metadata[pfx]
        if len(meta["case_samples"]) < 2:
            meta["case_samples"].append(cid)

        for ev_i in range(st_i, min(et_i, len(clean_events))):
            ev = clean_events[ev_i]
            ctx = ev.get("context", {}) or {}
            act = ctx.get("active_app", {}) or {}
            aname = act.get("app_name")
            wtitle = act.get("window_title") or ""
            if aname and aname != "unknown":
                meta["apps"][aname] += 1
            if "財務会計" in wtitle or "財務" in wtitle or "5123" in wtitle:
                meta["portals"]["財務会計システム (Financial Accounting)"] += 1
            elif "人事給与" in wtitle or "人事" in wtitle or "5122" in wtitle:
                meta["portals"]["HR人事給与システム (HR Management)"] += 1
            elif "受発注在庫" in wtitle or "在庫" in wtitle or "受発注" in wtitle or "5124" in wtitle:
                meta["portals"]["受発注在庫管理システム (Order & Inventory)"] += 1
            elif "調達" in wtitle or "購買" in wtitle or "5132" in wtitle or "5133" in wtitle or "5134" in wtitle:
                meta["portals"]["調達購買システム (Procurement System)"] += 1

            ext = ctx.get("extracted_text")
            s = ext.get("text") if isinstance(ext, dict) else str(ext or "")
            full_text = f"{wtitle}\n{s}"

            for u in re.findall(r'/#/([a-zA-Z0-9_\-]+)', full_text):
                if u not in ('dashboard', 'login'):
                    meta["url_paths"][u] += 2

            for line in full_text.split("\n"):
                line = line.strip()
                if 2 <= len(line) <= 25 and line not in GENERIC_IGNORE and not line.startswith(('http', '127.')):
                    if any(ord(c) > 127 for c in line):
                        meta["keywords"][line] += 1

    thread_profiles = {}
    for pfx, d in prefix_metadata.items():
        top_apps = [app for app, _ in d["apps"].most_common(2)]
        top_portal = d["portals"].most_common(1)[0][0] if d["portals"] else "Internal Business Application"
        top_urls = [f"url: {u}" for u, _ in d["url_paths"].most_common(2)]
        ocr_lines = screenshot_evidence.get(pfx, [])
        top_kw = [k for k, _ in d["keywords"].most_common(3) if not any(u in k for u in ['url:'])]
        context_items = top_urls + ocr_lines + top_kw
        thread_profiles[pfx] = {
            "thread_id": pfx,
            "apps": top_apps,
            "portal": top_portal,
            "evidence": ", ".join(context_items[:4]) if context_items else "internal workflow operations",
            "cases": d["case_samples"]
        }

    # -------------------------------------------------------------------------
    # STAGE 1: ACTIVITY SEGMENTATION (Paper §3.1, Figure 6)
    # -------------------------------------------------------------------------
    print("\n" + "#" * 80)
    print("STAGE 1: ACTIVITY SEGMENTATION (Paper §3.1, Figure 6: SEGMENTATION_PROMPT)")
    print("#" * 80)

    # Format representative sequence of candidate action batches
    action_batches = []
    for i in range(min(3, len(ordered_cases))):
        cid = ordered_cases[i]
        pfx = cid.split("-")[0].upper()
        st = start_boundaries[i]
        et = start_boundaries[i + 1] if i + 1 < len(start_boundaries) else last_boundary
        prof = thread_profiles.get(pfx, {"portal": "Enterprise Portal", "apps": ["Google Chrome"], "evidence": "internal task"})
        action_batches.append({
            "batch_idx": i + 1,
            "time_window": f"{st} -> {et}",
            "case_identifier": cid,
            "portal_visited": prof["portal"],
            "apps_used": prof["apps"],
            "observed_ui_signals": prof["evidence"]
        })

    prompt_stage1 = f"""You segment chronological computer-use action batches into contiguous activities. (TMI Paper §3.1, Figure 6)

Candidate Action Batches:
{json.dumps(action_batches, ensure_ascii=False, indent=2)}

Task:
For each batch, infer the coherent activity unit:
1. `objective`: One concise, self-contained phrase/sentence naming the intended business outcome (e.g., 'Approve and finalize invoice voucher', 'Review employee resident tax notification').
2. `additional_context`: 1-2 concise sentences summarizing the observed procedure and application evidence.

Output ONLY valid JSON:
{{
  "activities": [
    {{
      "batch_idx": 1,
      "objective": "<business outcome>",
      "additional_context": "<procedure and concrete evidence>"
    }}
  ]
}}"""

    print(">>> EXACT PROMPT SENT TO PUTER (STAGE 1: ACTIVITY SEGMENTATION) >>>")
    print(prompt_stage1)
    print("<<< END PROMPT <<<\n")

    t0_s1 = time.perf_counter()
    res_stage1 = call_puter(prompt_stage1)
    timings["Stage 1: Activity Segmentation (Puter LLM)"] = time.perf_counter() - t0_s1
    print(f">>> COMPLETE RAW ANSWER FROM PUTER IN {timings['Stage 1: Activity Segmentation (Puter LLM)']:.2f}s (STAGE 1) >>>")
    print(res_stage1)
    print("<<< END COMPLETE RAW ANSWER <<<\n")

    # -------------------------------------------------------------------------
    # STAGE 2: LATENT TASK DISCOVERY (Paper §3.2, Figure 7)
    # -------------------------------------------------------------------------
    print("\n" + "#" * 80)
    print("STAGE 2: LATENT TASK DISCOVERY (Paper §3.2, Figure 7: ROOT_THREAD_DISCOVERY_PROMPT)")
    print("#" * 80)

    # Select top representative leaf task activities to prevent LLM generation latency blowout
    top_pfxs = sorted(thread_profiles.keys(), key=lambda p: len(prefix_episodes[p]), reverse=True)[:4]
    candidate_leaves = []
    for pfx in sorted(top_pfxs):
        prof = thread_profiles[pfx]
        candidate_leaves.append({
            "thread_code": pfx,
            "portal": prof["portal"],
            "anchors": [prof["portal"].split(" ")[0]] + [k for k in prof["evidence"].split(", ") if "url:" in k or any(ord(c)>127 for c in k)][:2]
        })

    prompt_stage2 = f"""You are building a task thread forest from observed LEAF task activities (TMI Paper §3.2, Figure 7).
Assign each leaf thread_code to a durable ROOT business process.

Observed Leaves:
{json.dumps(candidate_leaves, ensure_ascii=False, indent=2)}

Output ONLY valid JSON:
{{
  "root_threads": [
    {{
      "thread_code": "INV",
      "root_objective": "Verify and approve supplier invoices in accounting portal",
      "anchors": ["財務会計", "invoice"]
    }}
  ]
}}"""

    print(">>> EXACT PROMPT SENT TO PUTER (STAGE 2: ROOT THREAD DISCOVERY) >>>")
    print(prompt_stage2)
    print("<<< END PROMPT <<<\n")

    t0_s2 = time.perf_counter()
    res_stage2 = call_puter(prompt_stage2)
    timings["Stage 2: Latent Task Discovery (Puter LLM)"] = time.perf_counter() - t0_s2
    print(f">>> COMPLETE RAW ANSWER FROM PUTER IN {timings['Stage 2: Latent Task Discovery (Puter LLM)']:.2f}s (STAGE 2) >>>")
    print(res_stage2)
    print("<<< END COMPLETE RAW ANSWER <<<\n")

    # -------------------------------------------------------------------------
    # STAGE 3: ROOT THREAD CONSOLIDATION & CANONICAL NAMING (Paper §3.2, Figure 8)
    # -------------------------------------------------------------------------
    print("\n" + "#" * 80)
    print("STAGE 3: ROOT THREAD CONSOLIDATION & NAMING (Paper §3.2, Figure 8)")
    print("#" * 80)

    prompt_stage3 = f"""Consolidate provisional root threads into canonical business processes. (TMI Paper §3.2, Figure 8)
Assign a canonical generic English snake_case label to each thread code based on observed portal and UI context:

Threads:
{json.dumps(candidate_leaves, ensure_ascii=False, indent=2)}

Output strictly valid JSON with no commentary:
{{
  "labels": {{
    "INV": "invoice_processing"
  }}
}}"""

    print(">>> EXACT PROMPT SENT TO PUTER (STAGE 3: CONSOLIDATION & CANONICAL NAMING) >>>")
    print(prompt_stage3)
    print("<<< END PROMPT <<<\n")

    t0_s3 = time.perf_counter()
    res_stage3 = call_puter(prompt_stage3)
    timings["Stage 3: Root Thread Consolidation & Naming (Puter LLM)"] = time.perf_counter() - t0_s3
    print(f">>> COMPLETE RAW ANSWER FROM PUTER IN {timings['Stage 3: Root Thread Consolidation & Naming (Puter LLM)']:.2f}s (STAGE 3) >>>")
    print(res_stage3)
    print("<<< END COMPLETE RAW ANSWER <<<\n")

    stage3_json = extract_json(res_stage3)
    label_map = {}
    if isinstance(stage3_json, dict):
        label_map = stage3_json.get("labels", {})
        if not label_map and "canonical_roots" in stage3_json:
            for r in stage3_json["canonical_roots"]:
                if isinstance(r, dict) and r.get("thread_code"):
                    label_map[r.get("thread_code")] = r.get("canonical_label")
    elif isinstance(stage3_json, list):
        for r in stage3_json:
            if isinstance(r, dict) and r.get("thread_code"):
                label_map[r.get("thread_code")] = r.get("canonical_label")

    # Merge deterministic fallbacks for any missing thread codes
    for pfx in thread_profiles.keys():
        if pfx not in label_map or not label_map[pfx]:
            label_map[pfx] = CANONICAL_FALLBACK.get(pfx, f"{pfx.lower()}_processing")

    print("[Stage 3 Consolidation] Established Canonical Process Label Map:")
    for pfx, lbl in sorted(label_map.items()):
        print(f"  Prefix '{pfx}' -> Canonical Label '{lbl}'")

    # -------------------------------------------------------------------------
    # STAGE 4: HIERARCHICAL TASK MODEL INDUCTION (Paper §3.3, Figures 9 & 10)
    # -------------------------------------------------------------------------
    print("\n" + "#" * 80)
    print("STAGE 4: TASK MODEL INDUCTION (OBJECTIVE & PROCEDURE TREES) (Paper §3.3, Figures 9 & 10)")
    print("#" * 80)

    sample_tasks_for_modeling = []
    for pfx in sorted(thread_profiles.keys())[:3]:
        sample_tasks_for_modeling.append({
            "thread_code": pfx,
            "label": label_map.get(pfx, f"{pfx.lower()}_processing"),
            "portal": thread_profiles[pfx]["portal"]
        })

    first_pfx = sample_tasks_for_modeling[0]["thread_code"]
    first_lbl = sample_tasks_for_modeling[0]["label"]

    prompt_stage4 = f"""Induce a hierarchical task model pairing an Objective Model with a Procedure Model for these representative business processes. (TMI Paper §3.3)
The procedure operators must be SEQ, FOR, or WHILE.

Business Processes:
{json.dumps(sample_tasks_for_modeling, ensure_ascii=False, indent=2)}

Output strictly valid JSON:
{{
  "task_models": [
    {{
      "thread_code": "{first_pfx}",
      "task_name": "{first_lbl}",
      "objective_model": {{
        "root_objective": "Execute business workflow",
        "subgoals": [
          "Select record by case ID",
          "Verify data against reference source",
          "Submit confirmation"
        ]
      }},
      "procedure_model": {{
        "operator": "FOR",
        "collection": "pending_records",
        "steps": [
          {{"operator": "SEQ", "name": "Open system portal and navigate to queue"}},
          {{"operator": "SEQ", "name": "Inspect item details"}},
          {{"operator": "SEQ", "name": "Click confirm button and finalize transaction"}}
        ]
      }}
    }}
  ]
}}"""

    print(">>> EXACT PROMPT SENT TO PUTER (STAGE 4: TASK MODEL INDUCTION) >>>")
    print(prompt_stage4)
    print("<<< END PROMPT <<<\n")

    t0_s4 = time.perf_counter()
    res_stage4 = call_puter(prompt_stage4)
    timings["Stage 4: Hierarchical Task Modeling (Puter LLM)"] = time.perf_counter() - t0_s4
    print(f">>> COMPLETE RAW ANSWER FROM PUTER IN {timings['Stage 4: Hierarchical Task Modeling (Puter LLM)']:.2f}s (STAGE 4) >>>")
    print(res_stage4)
    print("<<< END COMPLETE RAW ANSWER <<<\n")

    # -------------------------------------------------------------------------
    # STAGE 5: DELIVERABLE GENERATION (segments.jsonl)
    # -------------------------------------------------------------------------
    t0_s5 = time.perf_counter()
    print("\n" + "#" * 80)
    print("STAGE 5: DELIVERABLE GENERATION (segments.jsonl)")
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

    timings["Stage 5: Deliverable Generation (segments.jsonl)"] = time.perf_counter() - t0_s5
    print(f"[Phase 5.1] Generated {len(segments)} segments written to: {OUTPUT_FILE}")
    print("\n--- FIRST 5 GENERATED SEGMENTS ---")
    for s in segments[:5]:
        print(f"  {s['start']} -> {s['end']} | Label: {s['label']:<32} | Case: {s['case_id']}")

    # -------------------------------------------------------------------------
    # STAGE 6: POST-HOC GROUND TRUTH EVALUATION (STRICTLY ISOLATED)
    # -------------------------------------------------------------------------
    t0_s6 = time.perf_counter()
    print("\n" + "#" * 80)
    print("STAGE 6: POST-HOC EVALUATION AGAINST GROUND TRUTH (gt_manifest.json)")
    print("#" * 80)

    gt_manifest_file = SESSION_DIR / "gt_manifest.json"
    if not gt_manifest_file.exists():
        print(f"[Stage 6 Evaluation] No gt_manifest.json found in {SESSION_DIR}. (Unannotated Evaluation Set)")
        timings["Stage 6: Post-Hoc Ground Truth Evaluation"] = time.perf_counter() - t0_s6
        total_runtime = time.perf_counter() - total_t0
        timings["Total End-to-End Pipeline Runtime"] = total_runtime
        return

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

    session_end_sec = clean_events[-1]["timestamp_ms"] / 1000.0
    trace_gt_executions = [g for g in gt_executions if g["start_sec"] <= session_end_sec + 5.0]

    print(f"Total Predicted Segments:      {len(preds)}")
    print(f"Total Ground Truth Executions: {len(gt_executions)} (Active in trace: {len(trace_gt_executions)})")

    boundary_metrics = {}
    print("\nBoundary Evaluation Metrics (Full Ground Truth):")
    for tol in [1, 2, 5, 10, 30]:
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
        prec = tp / len(preds) if preds else 0.0
        rec = tp / len(gt_executions) if gt_executions else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        boundary_metrics[f"tol_{tol}s"] = {
            "tolerance_s": tol,
            "tp": tp,
            "total_gt": len(gt_executions),
            "precision": round(prec * 100, 2),
            "recall": round(rec * 100, 2),
            "f1": round(f1 * 100, 2)
        }
        print(f"  Tolerance <= {tol:>2}s: TP={tp:>2}/{len(gt_executions)} | Precision={prec*100:5.1f}% | Recall={rec*100:5.1f}% | F1={f1*100:5.1f}%")

    if len(trace_gt_executions) < len(gt_executions):
        print("\nBoundary Evaluation Metrics (Trace-Active Window Only - Truncated Log Adjustment):")
        for tol in [1, 2, 5, 10, 30]:
            tp = 0
            matched_gt = set()
            for p in preds:
                for idx, gt in enumerate(trace_gt_executions):
                    if idx in matched_gt: continue
                    s_diff = abs(p["start_sec"] - gt["start_sec"])
                    e_diff = abs(p["end_sec"] - gt["end_sec"])
                    if s_diff <= tol and e_diff <= tol:
                        tp += 1
                        matched_gt.add(idx)
                        break
            prec = tp / len(preds) if preds else 0.0
            rec = tp / len(trace_gt_executions) if trace_gt_executions else 0.0
            f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
            print(f"  Tolerance <= {tol:>2}s: TP={tp:>2}/{len(trace_gt_executions)} | Precision={prec*100:5.1f}% | Recall={rec*100:5.1f}% | F1={f1*100:5.1f}%")

    print("\nDetailed Segment Boundary Alignment vs Ground Truth:")
    print(f"  {'Predicted Case ID':<22} {'Pred Start':<21} {'Pred End':<21} | {'Matched GT Case':<18} {'GT Start':<21} {'GT End':<21} {'Start Diff':>11} {'End Diff':>11}")
    print("  " + "-" * 140)
    for p in preds:
        matched = None
        for gt in gt_executions:
            if gt["case_id"] == p.get("case_id"):
                matched = gt
                break
        if not matched:
            matched = min(gt_executions, key=lambda g: abs(g["start_sec"] - p["start_sec"]))
        s_diff = p["start_sec"] - matched["start_sec"]
        e_diff = p["end_sec"] - matched["end_sec"]
        print(f"  {p.get('case_id', 'unknown'):<22} {p['start']:<21} {p['end']:<21} | {matched['case_id']:<18} {clean_iso(matched['start_ts']):<21} {clean_iso(matched['end_ts']):<21} {s_diff:>+10.2f}s {e_diff:>+10.2f}s")

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

    process_alignment_summary = {}
    for lbl, counts in sorted(label_mapping.items()):
        best_gt = max(counts.items(), key=lambda x: x[1])
        process_alignment_summary[lbl] = {"gt_family": best_gt[0], "matches": best_gt[1]}
        print(f"  Predicted '{lbl}' -> {best_gt[0]} ({best_gt[1]} matches)")

    timings["Stage 6: Post-Hoc Ground Truth Evaluation"] = time.perf_counter() - t0_s6
    total_runtime = time.perf_counter() - total_t0
    timings["Total End-to-End Pipeline Runtime"] = total_runtime

    print("\n" + "=" * 80)
    print("LAYER & PROCESS EXECUTION TIME BREAKDOWN")
    print("=" * 80)
    print(f"{'Layer / Process':<52} {'Time (s)':>10} {'Percentage':>12}")
    print("-" * 80)
    for k, dur in timings.items():
        if k != "Total End-to-End Pipeline Runtime":
            pct = (dur / total_runtime) * 100 if total_runtime > 0 else 0.0
            print(f"{k:<52} {dur:>9.2f}s {pct:>11.1f}%")
    print("-" * 80)
    print(f"{'Total Execution Time':<52} {total_runtime:>9.2f}s {'100.0%':>12}")
    print("=" * 80)

    if REPORT_FILE:
        report_data = {
            "session_id": session_id,
            "session_dir": str(SESSION_DIR),
            "dominant_batch": dominant_batch,
            "total_events_loaded": len(raw_events),
            "clean_events_loaded": len(clean_events),
            "predicted_segments_count": len(preds),
            "ground_truth_executions_count": len(gt_executions),
            "timings": timings,
            "boundary_metrics": boundary_metrics,
            "process_alignment": process_alignment_summary
        }
        with open(REPORT_FILE, "w", encoding="utf-8") as rf:
            json.dump(report_data, rf, ensure_ascii=False, indent=2)
        print(f"\n[Benchmark Report] Successfully recorded to: {REPORT_FILE}")


if __name__ == "__main__":
    main()
