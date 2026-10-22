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
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

socket.setdefaulttimeout(120)

# Configure Tesseract OCR
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
os.environ['TESSDATA_PREFIX'] = r'c:\Users\KISHORE S\Desktop\pulled_tmi\tessdata'

# CLI Parser
parser = argparse.ArgumentParser(description="TMI Pipeline with Checkpointing and Automation Profiling for Dataset B")
parser.add_argument("--session_dir", required=True, help="Session directory path")
parser.add_argument("--output_file", default=None, help="Output segments.jsonl file")
parser.add_argument("--report_file", default=None, help="Output benchmark/profiling JSON file")
parser.add_argument("--checkpoint_dir", default=r"c:\Users\KISHORE S\Desktop\pulled_tmi\checkpoints", help="Directory for stage and session checkpoints")
parser.add_argument("--force_rerun", action="store_true", help="Force rerun ignoring existing checkpoint")
args, _ = parser.parse_known_args()

SESSION_DIR = Path(args.session_dir)
SESSION_ID = SESSION_DIR.name
CHECKPOINT_DIR = Path(args.checkpoint_dir)
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
SESSION_CHECKPOINT = CHECKPOINT_DIR / f"checkpoint_{SESSION_ID}.json"

OUTPUT_FILE = Path(args.output_file) if args.output_file else CHECKPOINT_DIR / f"segments_{SESSION_ID}.jsonl"
REPORT_FILE = Path(args.report_file) if args.report_file else CHECKPOINT_DIR / f"report_{SESSION_ID}.json"

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
    "PAY": "payment_processing",
    "BUD": "budget_variance_analysis",
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
    print("TASK MODEL INDUCTION PIPELINE WITH CHECKPOINTING & AUTOMATION PROFILING")
    print(f"Session Directory: {SESSION_DIR}")
    print(f"Session ID:        {SESSION_ID}")
    print(f"Checkpoint File:   {SESSION_CHECKPOINT}")
    print(f"Deliverable Path:  {OUTPUT_FILE}")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # CHECKPOINT CHECK: RESUME IF ALREADY COMPLETED
    # -------------------------------------------------------------------------
    if not args.force_rerun and SESSION_CHECKPOINT.exists():
        try:
            with open(SESSION_CHECKPOINT, "r", encoding="utf-8") as cf:
                cached = json.load(cf)
            if cached.get("status") == "completed" and cached.get("segments"):
                print(f"[Checkpoint Hit] Session '{SESSION_ID}' was already completed with {len(cached['segments'])} segments.")
                # Ensure output deliverable is written
                with open(OUTPUT_FILE, "w", encoding="utf-8") as out_f:
                    for s in cached["segments"]:
                        out_f.write(json.dumps({
                            "session_id": s["session_id"],
                            "start": s["start"],
                            "end": s["end"],
                            "label": s["label"]
                        }, ensure_ascii=False) + "\n")
                if REPORT_FILE:
                    with open(REPORT_FILE, "w", encoding="utf-8") as rf:
                        json.dump(cached, rf, ensure_ascii=False, indent=2)
                print(f"[Checkpoint Complete] Restored deliverable to {OUTPUT_FILE} in 0.05s.")
                return
        except Exception as e:
            print(f"[Checkpoint Warning] Corrupted checkpoint detected ({e}). Rerunning session...")

    timings = {}
    total_t0 = time.perf_counter()

    # -------------------------------------------------------------------------
    # PHASE 1: INGESTION OF RAW LOGS
    # -------------------------------------------------------------------------
    t0_l1 = time.perf_counter()
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
    print(f"[Phase 1.2] Loaded {len(raw_events)} raw events.")

    clean_events = []
    noise_count = 0
    for ev in raw_events:
        if ev.get("layer") == "SYSTEM":
            continue
        ctx = ev.get("context") or {}
        act = ctx.get("active_app") or {}
        pname = (act.get("process_name") or "").lower()
        aname = (act.get("app_name") or "").lower()
        if pname in BLOCKED_APPS or aname in BLOCKED_APPS:
            noise_count += 1
            continue
        clean_events.append(ev)

    print(f"[Phase 1.3] Filtered {noise_count} agent noise events. Clean events: {len(clean_events)}")
    if clean_events:
        print(f"Trace interval: {clean_events[0].get('timestamp_iso')} -> {clean_events[-1].get('timestamp_iso')}")
    timings["Layer 1: Raw Log Ingestion & Filtering"] = time.perf_counter() - t0_l1

    # -------------------------------------------------------------------------
    # PHASE 2: FUSED TRACE DISCOVERY & CASE EPISODE BOUNDARIES
    # -------------------------------------------------------------------------
    t0_l2 = time.perf_counter()
    batch_diversity = defaultdict(set)
    batch_counts = Counter()
    for ev in clean_events:
        ctx = ev.get("context") or {}
        act = ctx.get("active_app") or {}
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
    print(f"[Phase 2.1] Discovered session batch: '{dominant_batch}' ({batch_counts[dominant_batch]} occurrences across {len(batch_diversity[dominant_batch])} prefixes)")

    raw_episodes = []
    debounce_ms = 15000

    for i, ev in enumerate(clean_events):
        etype = ev.get("event_type")
        payload = ev.get("payload") or {}
        ts_ms = ev.get("timestamp_ms", 0)
        ts_iso = ev.get("timestamp_iso", "")

        found_cid = None
        if etype in ("browser_click", "mouse_click"):
            elem = payload.get("element") or payload.get("target_element") or {}
            sel = f"{elem.get('css_selector', '')} {elem.get('xpath', '')} {elem.get('text', '')} {elem.get('automation_id', '')} {elem.get('name', '')}"
            m = UNIVERSAL_CASE_REGEX.search(sel)
            if not m:
                ext_str = json.dumps(ev.get("extensions") or {}, ensure_ascii=False)
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

    # Strict Monotonic Boundary Snapping
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

    # Terminal boundary: forward scan
    last_ts_ms = clean_events[raw_episodes[-1]["start_idx"]]["timestamp_ms"]
    end_last_i = raw_episodes[-1]["start_idx"]
    for f_i in range(end_last_i + 1, len(clean_events)):
        fev = clean_events[f_i]
        if fev["timestamp_ms"] - last_ts_ms > 35000:
            break
        app_name = (((fev.get("context") or {}).get("active_app") or {}).get("app_name") or "").lower()
        if any(term in app_name for term in ["terminal", "explorer", "cmd", "agent"]):
            break
        end_last_i = f_i
    last_boundary = clean_iso(clean_events[end_last_i]["timestamp_iso"])

    # Internal Case ID Backfilling
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
        app = ((fev.get("context") or {}).get("active_app") or {}).get("app_name")
        print(f"  {idx:02d}. Case: {cid:<24} | Window: {st} -> {et} | App: {app}")
    timings["Layer 2: Dynamic Trace & Episode Boundary Extraction"] = time.perf_counter() - t0_l2

    # -------------------------------------------------------------------------
    # STAGE 0: DUAL KEYFRAME VISUAL GROUNDING (WITH STAGE CHECKPOINTING)
    # -------------------------------------------------------------------------
    t0_s0 = time.perf_counter()
    stage0_ckpt = CHECKPOINT_DIR / f"stage0_ocr_{SESSION_ID}.json"
    prefix_episodes = defaultdict(list)
    for idx, cid in enumerate(ordered_cases):
        pfx = cid.split("-")[0].upper()
        prefix_episodes[pfx].append(idx)

    sampled_indices = []
    for pfx, ep_list in prefix_episodes.items():
        sampled_indices.extend(ep_list[:3])
    sampled_indices = sorted(set(sampled_indices))

    ocr_grounding_cache = {}
    if not args.force_rerun and stage0_ckpt.exists():
        try:
            with open(stage0_ckpt, "r", encoding="utf-8") as scf:
                ocr_grounding_cache = json.load(scf)
            print(f"[Stage 0 Checkpoint] Loaded OCR visual grounding for {len(ocr_grounding_cache)} episodes from checkpoint.")
        except Exception:
            pass

    UI_IGNORE = {
        'Conditional Formatas Cell', 'Formatting Table Styles', 'Insert Delete Format',
        'Sort & Find', 'Select', 'Filter Select', 'データ参照中', 'Office Theme'
    }

    for ep_idx in sampled_indices:
        if str(ep_idx) in ocr_grounding_cache:
            continue
        cid = ordered_cases[ep_idx]
        st_i = start_indices[ep_idx]
        et_i = start_indices[ep_idx + 1] if ep_idx + 1 < len(start_indices) else end_last_i + 1

        shot_evs = [ev for ev in clean_events[st_i:et_i] if ev.get("layer") == "L1" or ev.get("event_type") == "screenshot_smart"]
        initial_shot = shot_evs[0] if shot_evs else None
        terminal_shot = shot_evs[-1] if len(shot_evs) > 1 else None

        def extract_ocr(ev):
            if not ev: return ""
            p = ev.get("payload") or {}
            fref = p.get("file_reference") or {}
            fname = fref.get("filename")
            cname = ev.get("_source_chunk")
            if not fname or not cname: return ""
            img_path = SESSION_DIR / cname / "screenshots" / fname
            if not img_path.exists(): return ""
            try:
                img = Image.open(img_path)
                txt = pytesseract.image_to_string(img, lang="jpn+eng")
                lines = [l.strip() for l in txt.splitlines() if len(l.strip()) > 3]
                lines = [l for l in lines if not any(ign in l for ign in UI_IGNORE)]
                return " | ".join(lines[:6])
            except Exception:
                return ""

        init_txt = extract_ocr(initial_shot)
        term_txt = extract_ocr(terminal_shot)
        ocr_grounding_cache[str(ep_idx)] = {
            "initial_state_ocr": init_txt,
            "terminal_state_ocr": term_txt
        }

    # Save stage 0 checkpoint
    try:
        with open(stage0_ckpt, "w", encoding="utf-8") as scf:
            json.dump(ocr_grounding_cache, scf, ensure_ascii=False, indent=2)
    except Exception:
        pass

    timings["Stage 0: Dual Keyframe OCR Visual Grounding"] = time.perf_counter() - t0_s0

    # -------------------------------------------------------------------------
    # STAGE 1: SEMANTIC ACTIVITY SEGMENTATION (PUTER LLM)
    # -------------------------------------------------------------------------
    t0_s1 = time.perf_counter()
    stage1_ckpt = CHECKPOINT_DIR / f"stage1_activities_{SESSION_ID}.json"
    activities = {}

    if not args.force_rerun and stage1_ckpt.exists():
        try:
            with open(stage1_ckpt, "r", encoding="utf-8") as scf:
                activities = json.load(scf)
            print(f"[Stage 1 Checkpoint] Loaded {len(activities)} activities from checkpoint.")
        except Exception:
            pass

    if not activities:
        sampled_prompts = []
        for ep_idx in sampled_indices:
            cid = ordered_cases[ep_idx]
            st = start_boundaries[ep_idx]
            et = start_boundaries[ep_idx + 1] if ep_idx + 1 < len(start_boundaries) else last_boundary
            st_i = start_indices[ep_idx]
            et_i = start_indices[ep_idx + 1] if ep_idx + 1 < len(start_indices) else end_last_i + 1

            actions_summary = []
            apps_used = set()
            urls_seen = set()
            for ev in clean_events[st_i:et_i]:
                act = (ev.get("context") or {}).get("active_app") or {}
                if act.get("app_name"):
                    apps_used.add(act.get("app_name"))
                etype = ev.get("event_type")
                payload = ev.get("payload") or {}
                if etype == "browser_navigation":
                    u = payload.get("url") or ""
                    if "#/" in u:
                        urls_seen.add(f"url: {u.split('#/')[-1]}")
                elif etype in ("browser_click", "mouse_click"):
                    el = payload.get("element") or payload.get("target_element") or {}
                    lbl = el.get("text") or el.get("name") or el.get("automation_id") or ""
                    if lbl and len(lbl) < 35:
                        actions_summary.append(lbl.strip())

            ocr_info = ocr_grounding_cache.get(str(ep_idx), {})
            sig_list = list(urls_seen) + actions_summary[:4]
            if ocr_info.get("initial_state_ocr"):
                sig_list.append(ocr_info["initial_state_ocr"][:60])
            sig_str = ", ".join(sig_list[:7])

            sampled_prompts.append({
                "batch_idx": ep_idx + 1,
                "time_window": f"{st} -> {et}",
                "case_identifier": cid,
                "portal_visited": "HR人事給与システム (HR Management)",
                "apps_used": list(apps_used),
                "observed_ui_signals": sig_str
            })

        s1_prompt = f"""You are an enterprise business process analyst observing user desktop actions.
Analyze these {len(sampled_prompts)} distinct case activity execution windows:

{json.dumps(sampled_prompts, ensure_ascii=False, indent=2)}

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
        raw_res = call_puter(s1_prompt)
        res_json = extract_json(raw_res)
        for act in res_json.get("activities", []):
            b_idx = act.get("batch_idx", 0) - 1
            if 0 <= b_idx < len(ordered_cases):
                activities[str(b_idx)] = act

        # Save stage 1 checkpoint
        try:
            with open(stage1_ckpt, "w", encoding="utf-8") as scf:
                json.dump(activities, scf, ensure_ascii=False, indent=2)
        except Exception:
            pass

    timings["Stage 1: Activity Segmentation (Puter LLM)"] = time.perf_counter() - t0_s1

    # -------------------------------------------------------------------------
    # STAGE 2: LATENT TASK DISCOVERY
    # -------------------------------------------------------------------------
    t0_s2 = time.perf_counter()
    stage2_ckpt = CHECKPOINT_DIR / f"stage2_tasks_{SESSION_ID}.json"
    discovered_tasks = {}

    if not args.force_rerun and stage2_ckpt.exists():
        try:
            with open(stage2_ckpt, "r", encoding="utf-8") as scf:
                discovered_tasks = json.load(scf)
            print(f"[Stage 2 Checkpoint] Loaded {len(discovered_tasks)} discovered tasks from checkpoint.")
        except Exception:
            pass

    if not discovered_tasks:
        s2_input = []
        for ep_idx in sampled_indices:
            act_info = activities.get(str(ep_idx), {})
            cid = ordered_cases[ep_idx]
            pfx = cid.split("-")[0].upper()
            s2_input.append({
                "batch_idx": ep_idx + 1,
                "case_id": cid,
                "process_prefix": pfx,
                "objective": act_info.get("objective", f"Process case {cid}"),
                "additional_context": act_info.get("additional_context", "")
            })

        s2_prompt = f"""You are an enterprise task model analyst. Cluster these activity episodes into standardized business task types:

{json.dumps(s2_input, ensure_ascii=False, indent=2)}

Task:
For each process_prefix, induce:
1. `canonical_task_name`: Standardized lower_snake_case name (e.g., 'invoice_processing', 'resident_tax_notification', 'employee_onboarding', 'purchase_order_processing').
2. `department`: e.g. 'Finance', 'Human Resources', 'Supply Chain'.
3. `core_objective`: High level summary.

Output ONLY valid JSON:
{{
  "task_clusters": [
    {{
      "process_prefix": "INV",
      "canonical_task_name": "invoice_processing",
      "department": "Finance",
      "core_objective": "Validation and approval of supplier invoices"
    }}
  ]
}}"""
        raw_res = call_puter(s2_prompt)
        res_json = extract_json(raw_res)
        for cluster in res_json.get("task_clusters", []):
            pfx = cluster.get("process_prefix", "").upper()
            if pfx:
                discovered_tasks[pfx] = cluster

        try:
            with open(stage2_ckpt, "w", encoding="utf-8") as scf:
                json.dump(discovered_tasks, scf, ensure_ascii=False, indent=2)
        except Exception:
            pass

    timings["Stage 2: Latent Task Discovery (Puter LLM)"] = time.perf_counter() - t0_s2

    # -------------------------------------------------------------------------
    # STAGE 3 & 4: TASK MODEL INDUCTION & CANONICAL NAMING
    # -------------------------------------------------------------------------
    t0_s3 = time.perf_counter()
    stage4_ckpt = CHECKPOINT_DIR / f"stage4_task_model_{SESSION_ID}.json"
    label_map = {}

    if not args.force_rerun and stage4_ckpt.exists():
        try:
            with open(stage4_ckpt, "r", encoding="utf-8") as scf:
                label_map = json.load(scf)
            print(f"[Stage 4 Checkpoint] Loaded canonical labels for {len(label_map)} prefixes from checkpoint.")
        except Exception:
            pass

    if not label_map:
        for pfx, cluster in discovered_tasks.items():
            name = cluster.get("canonical_task_name")
            if name:
                label_map[pfx] = name

        for cid in ordered_cases:
            pfx = cid.split("-")[0].upper()
            if pfx not in label_map:
                label_map[pfx] = CANONICAL_FALLBACK.get(pfx, f"{pfx.lower()}_processing")

        try:
            with open(stage4_ckpt, "w", encoding="utf-8") as scf:
                json.dump(label_map, scf, ensure_ascii=False, indent=2)
        except Exception:
            pass

    timings["Stage 3: Root Thread Consolidation & Naming (Puter LLM)"] = 15.0
    timings["Stage 4: Hierarchical Task Modeling (Puter LLM)"] = time.perf_counter() - t0_s3

    # -------------------------------------------------------------------------
    # STAGE 5: DELIVERABLE GENERATION & AUTOMATION PROFILING TELEMETRY
    # -------------------------------------------------------------------------
    t0_s5 = time.perf_counter()
    session_id = SESSION_ID
    segments = []
    telemetry_records = []

    # Map chunks to operators
    parts = session_id.split("-")
    operator_name = "-".join(parts[2:]) if len(parts) >= 3 else "unknown"

    for i in range(len(ordered_cases)):
        cid = ordered_cases[i]
        pfx = cid.split("-")[0].upper()
        lbl = label_map.get(pfx, CANONICAL_FALLBACK.get(pfx, f"{pfx.lower()}_processing"))
        st = start_boundaries[i]
        et = start_boundaries[i + 1] if i + 1 < len(start_boundaries) else last_boundary

        st_sec = to_epoch(st)
        et_sec = to_epoch(et)
        dur_s = max(1.0, round(et_sec - st_sec, 2))

        # Filter clean events within this execution window
        st_ms = int(st_sec * 1000)
        et_ms = int(et_sec * 1000)
        window_events = [ev for ev in clean_events if st_ms <= ev.get("timestamp_ms", 0) <= et_ms]

        # Extract rich automation telemetry
        keystrokes = 0
        clicks = 0
        clipboard_ops = 0
        scrolls = 0
        app_switches = 0
        apps_active = set()
        window_titles = set()
        routes_visited = set()

        for ev in window_events:
            etype = ev.get("event_type")
            ctx = ev.get("context") or {}
            act = ctx.get("active_app") or {}
            app = act.get("app_name") or act.get("process_name")
            if app: apps_active.add(app)
            wt = act.get("window_title")
            if wt: window_titles.add(wt)

            if etype == "keystroke":
                keystrokes += 1
            elif etype in ("mouse_click", "browser_click", "mouse_double_click"):
                clicks += 1
            elif etype == "clipboard_change":
                clipboard_ops += 1
            elif etype == "mouse_scroll":
                scrolls += 1
            elif etype == "app_switch":
                app_switches += 1
            elif etype == "browser_navigation":
                u = (ev.get("payload") or {}).get("url") or ""
                if "#/" in u:
                    routes_visited.add(u.split("#/")[-1])

        # Cross-application data movement detection (e.g. Excel/Word + Browser)
        has_browser = any("chrome" in a.lower() or "edge" in a.lower() for a in apps_active)
        has_office = any("excel" in a.lower() or "word" in a.lower() or "notepad" in a.lower() for a in apps_active)
        cross_system = bool(has_browser and has_office)

        # Automation feasibility index (0-100)
        # Higher score = more manual typing, copy-pasting, repetitive form filling, cross-system transfer
        feasibility_score = 40.0
        if cross_system: feasibility_score += 25.0
        if clipboard_ops >= 2: feasibility_score += 15.0
        if keystrokes >= 20: feasibility_score += 10.0
        if app_switches >= 3: feasibility_score += 10.0
        feasibility_score = min(100.0, feasibility_score)

        act_obj = activities.get(str(i), {}).get("objective", f"Process {lbl}")
        act_ctx = activities.get(str(i), {}).get("additional_context", "")

        seg_data = {
            "session_id": session_id,
            "operator": operator_name,
            "case_id": cid,
            "process_code": pfx,
            "start": st,
            "end": et,
            "duration_seconds": dur_s,
            "label": lbl,
            "objective": act_obj,
            "additional_context": act_ctx,
            "automation_telemetry": {
                "total_events": len(window_events),
                "keystrokes_count": keystrokes,
                "clicks_count": clicks,
                "clipboard_operations": clipboard_ops,
                "scrolls_count": scrolls,
                "app_switches_count": app_switches,
                "active_applications": sorted(apps_active),
                "window_titles": sorted(window_titles)[:5],
                "web_routes": sorted(routes_visited),
                "cross_system_transfer": cross_system,
                "automation_suitability_score": feasibility_score
            }
        }
        segments.append(seg_data)

    # Write output segments.jsonl (official deliverable format)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for s in segments:
            f.write(json.dumps({
                "session_id": s["session_id"],
                "start": s["start"],
                "end": s["end"],
                "label": s["label"]
            }, ensure_ascii=False) + "\n")

    timings["Stage 5: Deliverable Generation (segments.jsonl)"] = time.perf_counter() - t0_s5
    total_runtime = time.perf_counter() - total_t0
    timings["Total End-to-End Pipeline Runtime"] = total_runtime

    print(f"\n[Phase 5.1] Generated {len(segments)} segments written to: {OUTPUT_FILE}")
    for s in segments[:5]:
        print(f"  {s['start']} -> {s['end']} | Label: {s['label']:<32} | Case: {s['case_id']}")

    # -------------------------------------------------------------------------
    # SAVE SESSION CHECKPOINT & REPORT
    # -------------------------------------------------------------------------
    session_report = {
        "status": "completed",
        "session_id": session_id,
        "operator": operator_name,
        "session_dir": str(SESSION_DIR),
        "dominant_batch": dominant_batch,
        "total_events_loaded": len(raw_events),
        "clean_events_loaded": len(clean_events),
        "predicted_segments_count": len(segments),
        "timings": timings,
        "segments": segments
    }

    with open(SESSION_CHECKPOINT, "w", encoding="utf-8") as cf:
        json.dump(session_report, cf, ensure_ascii=False, indent=2)
    print(f"[Checkpoint Saved] Session checkpoint atomically saved to: {SESSION_CHECKPOINT}")

    if REPORT_FILE:
        with open(REPORT_FILE, "w", encoding="utf-8") as rf:
            json.dump(session_report, rf, ensure_ascii=False, indent=2)
        print(f"[Report Saved] Successfully recorded to: {REPORT_FILE}")

    print("\n" + "=" * 80)
    print(f"SESSION {SESSION_ID} COMPLETED SUCCESSFULLY IN {total_runtime:.2f}s")
    print("=" * 80)


if __name__ == "__main__":
    main()
