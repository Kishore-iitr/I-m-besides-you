"""
Multi-Step Task Model Induction (TMI) Pipeline with Full LLM Visibility
Strictly adheres to Jiang et al. (arXiv:2608.20319v1) Appendix F Prompts:
- Stage 1: Activity Segmentation (Figure 6: SEGMENTATION_PROMPT)
- Stage 2: Latent Task Discovery (Figure 7: ROOT_THREAD_DISCOVERY_PROMPT)
- Stage 3: Root Thread Consolidation & Naming (Figure 8: ROOT_THREAD_CONSOLIDATION_PROMPT)
- Stage 4: Hierarchical Objective & Procedure Modeling (Figures 9 & 10)
- Stage 5: Segment Assembly & Deliverable Generation (segments.jsonl)
- Stage 6: Post-Hoc Ground Truth Evaluation (gt_manifest.json)

Provides complete, transparent logging of EVERY Puter LLM prompt and COMPLETE raw response.
"""

import argparse
import os
import re
import sys
import json
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pytesseract
from PIL import Image

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
parser = argparse.ArgumentParser(description="Multi-Step Task Model Induction Pipeline with Screenshot Grounding")
parser.add_argument("--session_dir", default=r"G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_a\ses_20260701-055037-Marcos")
parser.add_argument("--output_file", default=r"c:\Users\KISHORE S\Desktop\pulled_tmi\segments.jsonl")
args, _ = parser.parse_known_args()

SESSION_DIR = Path(args.session_dir)
OUTPUT_FILE = Path(args.output_file)

PUTER_TOKEN = os.environ.get(
    "PUTER_AUTH_TOKEN",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6InYyIn0.eyJ0IjoiYXUiLCJ2IjoiMiIsInV1IjoiZ0dXcTBPVE1TdEdSWkZWK2RQZEFWZz09IiwiYXUiOiJKaFNmQzRNRVVpaTVsWGN0cmM5QkRnPT0iLCJzdSI6ImhUS1diTTNnVCtxMHBvVHZpT2JsMUE9PSIsImFpIjoiZ0dXcTBPVE1TdEdSWkZWK2RQZEFWZz09IiwiaWF0IjoxNzkyNTY1OTE4fQ.XrFC2-zDsTcgmO7ioM3kXqu89Wqf48fkFaxZZQs1k1U"
)
PUTER_MODEL = os.environ.get("PUTER_MODEL", "openrouter:minimax/minimax-m3.1-flash:free")
PUTER_URL = "https://api.puter.com/drivers/call"

THREE_PART_REGEX = re.compile(r'\b([A-Z]{2,6})[-_](\d{4,8})[-_](\d{2,4})\b')
BLOCKED_APPS = {"procmine-desktop-agent.exe", "procmine-desktop-agent", "omapsvcbroker.exe"}


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
    time.sleep(5)  # Rate-limit guard for Puter API
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

    req = urllib.request.Request(
        PUTER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {PUTER_TOKEN}"},
        method="POST"
    )

    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=120) as res:
                data = json.loads(res.read().decode("utf-8"))
                return data.get("result", {}).get("message", {}).get("content", "")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait_sec = 20 * (attempt + 1)
                print(f"[Puter API 429 Concurrency Lock] Waiting {wait_sec}s before retry...", file=sys.stderr, flush=True)
                time.sleep(wait_sec)
                continue
            elif attempt < 5:
                print(f"[Puter API HTTP {e.code}] Retrying in 10s...", file=sys.stderr, flush=True)
                time.sleep(10)
                continue
            raise e
        except Exception as e:
            if attempt < 5:
                print(f"[Puter API Warning] Call failed ({e}), retrying in 10s...", file=sys.stderr, flush=True)
                time.sleep(10)
            else:
                raise e
    return ""


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
    print("=" * 80)

    # -------------------------------------------------------------------------
    # INGESTION & EVENT FILTERING
    # -------------------------------------------------------------------------
    print("\n" + "#" * 80)
    print("PHASE 1: INGESTION OF RAW OPERATION LOGS (events.jsonl)")
    print("#" * 80)

    chunk_dirs = sorted([p for p in SESSION_DIR.iterdir() if p.is_dir() and "chunk_" in p.name])
    print(f"[Phase 1.1] Discovered {len(chunk_dirs)} recording chunk(s): {[c.name for c in chunk_dirs]}")

    raw_events = []
    for cdir in chunk_dirs:
        ev_file = cdir / "events.jsonl"
        with open(ev_file, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    ev = json.loads(line)
                    ev["_source_chunk"] = cdir.name
                    ev["_line_no"] = line_no
                    raw_events.append(ev)

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

    # -------------------------------------------------------------------------
    # TRACE DISCOVERY & CASE GROUPING
    # -------------------------------------------------------------------------
    print("\n" + "#" * 80)
    print("PHASE 2: DYNAMIC TRACE DISCOVERY & CASE EPISODE EXTRACTION")
    print("#" * 80)

    batch_diversity = defaultdict(set)
    batch_counts = Counter()
    for ev in clean_events:
        text = " ".join([
            ev.get("context", {}).get("active_app", {}).get("window_title", ""),
            str(ev.get("context", {}).get("extracted_text", "")),
            str(ev.get("payload", {}))
        ])
        for m in THREE_PART_REGEX.finditer(text):
            pfx = m.group(1).upper()
            batch_id = m.group(2)
            batch_counts[batch_id] += 1
            batch_diversity[batch_id].add(pfx)

    # Dominant enterprise batch is the one spanning the highest diversity of distinct task prefixes
    dominant_batch = max(batch_diversity.keys(), key=lambda b: len(batch_diversity[b]))
    print(f"[Phase 2.1] Discovered enterprise session batch: '{dominant_batch}' ({batch_counts[dominant_batch]} occurrences across {len(batch_diversity[dominant_batch])} process prefixes: {sorted(batch_diversity[dominant_batch])})")

    # Extract case first and last indices
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
    print(f"\n[Phase 2.2] Identified {len(ordered_cases)} distinct case executions in chronological order:")
    for idx, cid in enumerate(ordered_cases, 1):
        fev = clean_events[case_first_idx[cid]]
        app = fev.get("context", {}).get("active_app", {}).get("app_name")
        print(f"  {idx:02d}. Case: {cid:<16} | First Seen: {fev['timestamp_iso']} | App: {app}")

    # -------------------------------------------------------------------------
    # STAGE 0: DUAL KEYFRAME VISUAL GROUNDING (INITIAL + TERMINAL) (Paper §3.1)
    # -------------------------------------------------------------------------
    print("\n" + "#" * 80)
    print("STAGE 0: DUAL KEYFRAME VISUAL GROUNDING (INITIAL + TERMINAL FRAMES)")
    print("#" * 80)

    UI_IGNORE = {
        'Conditional Formatas Cell', 'Formatting Table Styles', 'Insert Delete Format',
        'Sort & Find', 'Select', 'Filter Select', 'データ参照中', 'Office Theme'
    }

    screenshot_evidence = defaultdict(list)
    for pfx in sorted(batch_diversity[dominant_batch]):
        matching = [c for c in ordered_cases if c.startswith(f"{pfx}-")]
        if not matching:
            continue
        sample_cid = matching[0]
        st_i = case_first_idx[sample_cid]
        et_i = case_last_idx[sample_cid]

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
        for j in range(et_i, max(0, et_i - 30), -1):
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
            print(f"[Stage 0 Dual OCR: {pfx:<4}] {len(imgs_to_ocr)} keyframe(s) -> Grounded UI: {collected[:3]}")

    # Boundary snapping
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

    last_cid = ordered_cases[-1]
    last_case_i = case_last_idx[last_cid]
    end_last_i = last_case_i
    for f_i in range(last_case_i, len(clean_events)):
        fev = clean_events[f_i]
        if fev["timestamp_ms"] - clean_events[end_last_i]["timestamp_ms"] > 15000:
            break
        end_last_i = f_i
    last_boundary = clean_iso(clean_events[end_last_i]["timestamp_iso"])

    # Extract observed UI evidence per thread prefix
    GENERIC_IGNORE = {
        'ダッシュボード', '2026年度', 'HR人事給与システム', '受発注在庫管理システム',
        '財務会計システム', 'Google Chrome', 'Notepad', 'Microsoft Word', 'Excel',
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
            if "財務会計" in wtitle or "財務" in wtitle:
                meta["portals"]["財務会計システム (Financial Accounting)"] += 1
            elif "人事給与" in wtitle or "人事" in wtitle:
                meta["portals"]["HR人事給与システム (HR Management)"] += 1
            elif "受発注在庫" in wtitle or "在庫" in wtitle or "受発注" in wtitle:
                meta["portals"]["受発注在庫管理システム (Order & Inventory)"] += 1

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
    for i in range(min(4, len(ordered_cases))):
        cid = ordered_cases[i]
        pfx = cid.split("-")[0]
        st = start_boundaries[i]
        et = start_boundaries[i + 1] if i + 1 < len(start_boundaries) else last_boundary
        prof = thread_profiles[pfx]
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

    t0 = time.time()
    res_stage1 = call_puter(prompt_stage1)
    print(f">>> COMPLETE RAW ANSWER FROM PUTER IN {time.time()-t0:.2f}s (STAGE 1) >>>")
    print(res_stage1)
    print("<<< END COMPLETE RAW ANSWER <<<\n")

    # -------------------------------------------------------------------------
    # STAGE 2: LATENT TASK DISCOVERY (Paper §3.2, Figure 7)
    # -------------------------------------------------------------------------
    print("\n" + "#" * 80)
    print("STAGE 2: LATENT TASK DISCOVERY (Paper §3.2, Figure 7: ROOT_THREAD_DISCOVERY_PROMPT)")
    print("#" * 80)

    candidate_leaves = []
    for pfx in sorted(thread_profiles.keys()):
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

    t0 = time.time()
    res_stage2 = call_puter(prompt_stage2)
    print(f">>> COMPLETE RAW ANSWER FROM PUTER IN {time.time()-t0:.2f}s (STAGE 2) >>>")
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
  "canonical_roots": [
    {{
      "thread_code": "INV",
      "canonical_label": "invoice_processing",
      "business_objective": "Verify and approve supplier invoices in accounting portal",
      "deliverable": "Approved invoice record"
    }}
  ],
  "labels": {{
    "INV": "invoice_processing"
  }}
}}"""

    print(">>> EXACT PROMPT SENT TO PUTER (STAGE 3: CONSOLIDATION & CANONICAL NAMING) >>>")
    print(prompt_stage3)
    print("<<< END PROMPT <<<\n")

    t0 = time.time()
    res_stage3 = call_puter(prompt_stage3)
    print(f">>> COMPLETE RAW ANSWER FROM PUTER IN {time.time()-t0:.2f}s (STAGE 3) >>>")
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

    t0 = time.time()
    res_stage4 = call_puter(prompt_stage4)
    print(f">>> COMPLETE RAW ANSWER FROM PUTER IN {time.time()-t0:.2f}s (STAGE 4) >>>")
    print(res_stage4)
    print("<<< END COMPLETE RAW ANSWER <<<\n")

    # -------------------------------------------------------------------------
    # STAGE 5: DELIVERABLE GENERATION (segments.jsonl)
    # -------------------------------------------------------------------------
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

    print(f"[Phase 5.1] Generated {len(segments)} segments written to: {OUTPUT_FILE}")
    print("\n--- FIRST 5 GENERATED SEGMENTS ---")
    for s in segments[:5]:
        print(f"  {s['start']} -> {s['end']} | Label: {s['label']:<32} | Case: {s['case_id']}")

    # -------------------------------------------------------------------------
    # STAGE 6: POST-HOC GROUND TRUTH EVALUATION (STRICTLY ISOLATED)
    # -------------------------------------------------------------------------
    print("\n" + "#" * 80)
    print("STAGE 6: POST-HOC EVALUATION AGAINST GROUND TRUTH (gt_manifest.json)")
    print("#" * 80)

    gt_manifest_file = SESSION_DIR / "gt_manifest.json"
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
