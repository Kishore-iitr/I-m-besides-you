import sys
import os
import json
import time
import urllib.request
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
from typing import List, Dict, Any, Optional
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

DATASET_B_DIR = Path(r"G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_b")
PROFILING_FILE = Path(r"c:\Users\KISHORE S\Desktop\pulled_tmi\dataset_b_automation_profiling.json")
OUTPUT_MD = Path(r"c:\Users\KISHORE S\Desktop\pulled_tmi\INVOICE_PROCESSING_PROCESS_GUIDE.md")
OUTPUT_JSON = Path(r"c:\Users\KISHORE S\Desktop\pulled_tmi\invoice_processing_sop.json")
EVIDENCE_JSON = Path(r"c:\Users\KISHORE S\Desktop\pulled_tmi\invoice_multimodal_evidence.json")

PUTER_TOKEN = os.environ.get(
    "PUTER_AUTH_TOKEN",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6InYyIn0.eyJ0IjoiYXUiLCJ2IjoiMiIsInV1IjoiZ0dXcTBPVE1TdEdSWkZWK2RQZEFWZz09IiwiYXUiOiJKaFNmQzRNRVVpaTVsWGN0cmM5QkRnPT0iLCJzdSI6ImhUS1diTTNnVCtxMHBvVHZpT2JsMUE9PSIsImFpIjoiZ0dXcTBPVE1TdEdSWkZWK2RQZEFWZz09IiwiaWF0IjoxNzkyNTY1OTE4fQ.XrFC2-zDsTcgmO7ioM3kXqu89Wqf48fkFaxZZQs1k1U"
)
PUTER_MODEL = "openrouter:minimax/minimax-m3.1-flash:free"
PUTER_URL = "https://api.puter.com/drivers/call"


def call_llm(prompt: str, system_prompt: str = "You are a lead enterprise workflow architect and RPA specialist.") -> str:
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
    for attempt in range(5):
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
        except Exception as e:
            time.sleep(5 * (attempt + 1))
    return ""


def extract_ocr_from_image(img_path: Path) -> List[str]:
    if not img_path.exists():
        return []
    try:
        img = Image.open(img_path)
        txt = pytesseract.image_to_string(img, lang="jpn+eng")
        lines = [l.strip() for l in txt.splitlines() if len(l.strip()) > 2]
        return lines
    except Exception:
        return []


def main():
    print("=" * 90)
    print("DEDICATED INVOICE PROCESSING DEEP-DIVE & REVERSE-ENGINEERING PIPELINE")
    print(f"Dataset B Path: {DATASET_B_DIR}")
    print(f"Target Output:  {OUTPUT_MD}")
    print("=" * 90)

    # 1. Load recovered segments from Dataset B profiling
    with open(PROFILING_FILE, "r", encoding="utf-8") as pf:
        profiling = json.load(pf)

    all_segments = profiling.get("all_segments_telemetry", [])
    invoice_segments = [s for s in all_segments if "invoice" in s.get("label", "").lower()]
    print(f"[Step 1] Identified {len(invoice_segments)} total invoice processing segments in Dataset B.")

    # Group segments by operator to ensure representative cross-operator sampling
    by_operator = defaultdict(list)
    for s in invoice_segments:
        by_operator[s.get("operator", "unknown")].append(s)

    selected_cases = []
    # Sample up to 3 diverse cases from each operator (total ~12 cases)
    for op, segs in by_operator.items():
        # Pick shortest, medium, and longest duration cases to capture variance
        sorted_segs = sorted(segs, key=lambda x: x.get("duration_seconds", 0))
        if len(sorted_segs) <= 3:
            selected_cases.extend(sorted_segs)
        else:
            selected_cases.append(sorted_segs[0])  # shortest
            selected_cases.append(sorted_segs[len(sorted_segs) // 2])  # median
            selected_cases.append(sorted_segs[-1])  # longest

    print(f"[Step 2] Selected {len(selected_cases)} representative invoice cases across {len(by_operator)} operators:")
    for c in selected_cases:
        print(f"  Operator: {c.get('operator'):<16} | Case: {c.get('case_id'):<16} | Duration: {c.get('duration_seconds'):4.1f}s | Session: {c.get('session_id')}")

    # 2. Extract raw events and screenshots for each selected case
    print("\n[Step 3] Extracting granular action traces, UI elements, and screenshot OCR...")
    case_evidence_dossiers = []

    # Cache chunk events to avoid re-reading disk
    chunk_events_cache = {}

    for idx, seg in enumerate(selected_cases, 1):
        sid = seg["session_id"]
        cid = seg["case_id"]
        st = seg["start"]
        et = seg["end"]
        op = seg.get("operator", "unknown")
        sdir = DATASET_B_DIR / sid

        st_ms = int(datetime.fromisoformat(st.replace("Z", "+00:00")).timestamp() * 1000)
        et_ms = int(datetime.fromisoformat(et.replace("Z", "+00:00")).timestamp() * 1000)

        # Load events for this session if not cached
        if sid not in chunk_events_cache:
            chunks = sorted([p for p in sdir.iterdir() if p.is_dir() and "chunk" in p.name])
            evs = []
            for c in chunks:
                ef = c / "events.jsonl"
                if ef.exists():
                    for line in open(ef, encoding="utf-8"):
                        if line.strip():
                            try:
                                item = json.loads(line)
                                item["_chunk"] = c.name
                                evs.append(item)
                            except Exception:
                                pass
            evs.sort(key=lambda x: x.get("timestamp_ms", 0))
            chunk_events_cache[sid] = evs

        session_evs = chunk_events_cache[sid]
        case_evs = [e for e in session_evs if st_ms <= e.get("timestamp_ms", 0) <= et_ms and e.get("layer") != "SYSTEM"]

        # Parse actions
        action_steps = []
        screenshots_captured = []
        ocr_texts = {}

        for e in case_evs:
            t = e.get("timestamp_iso", "")
            etype = e.get("event_type")
            payload = e.get("payload") or {}
            ctx = e.get("context") or {}
            act = ctx.get("active_app") or {}
            app_name = act.get("app_name") or act.get("process_name") or ""
            window_title = act.get("window_title") or ""

            if etype == "screenshot_smart":
                fref = payload.get("file_reference") or {}
                fname = fref.get("filename")
                if fname:
                    img_path = sdir / e.get("_chunk", "") / "screenshots" / fname
                    screenshots_captured.append({
                        "filename": fname,
                        "timestamp": t,
                        "trigger": payload.get("trigger_reason"),
                        "app": app_name,
                        "window_title": window_title,
                        "image_path": str(img_path)
                    })
                    # OCR sample screenshots (initial, mid, terminal)
                    if len(screenshots_captured) in (1, 3, 5, len(case_evs)):
                        ocr_lines = extract_ocr_from_image(img_path)
                        ocr_texts[fname] = ocr_lines[:10]

            elif etype in ("browser_click", "mouse_click"):
                elem = payload.get("element") or payload.get("target_element") or {}
                txt = elem.get("text") or elem.get("name") or elem.get("automation_id") or ""
                tag = elem.get("tag_name") or ""
                coords = payload.get("click_coordinates") or payload.get("coordinates") or {}
                action_steps.append({
                    "time": t,
                    "action_type": "CLICK",
                    "app": app_name,
                    "target_text": txt.strip(),
                    "tag": tag,
                    "coordinates": coords,
                    "window_title": window_title
                })
            elif etype == "keystroke":
                key = payload.get("key")
                char = payload.get("character")
                action_steps.append({
                    "time": t,
                    "action_type": "KEYSTROKE",
                    "app": app_name,
                    "key": key,
                    "char": char,
                    "window_title": window_title
                })
            elif etype == "clipboard_change":
                action_steps.append({
                    "time": t,
                    "action_type": "CLIPBOARD_PASTE",
                    "app": app_name,
                    "formats": payload.get("formats_available"),
                    "length": payload.get("text_length"),
                    "window_title": window_title
                })
            elif etype == "app_switch":
                new_app = (payload.get("new_app") or {}).get("app_name", "")
                new_title = (payload.get("new_app") or {}).get("window_title", "")
                action_steps.append({
                    "time": t,
                    "action_type": "APP_SWITCH",
                    "from_app": app_name,
                    "to_app": new_app,
                    "new_title": new_title
                })
            elif etype == "browser_navigation":
                action_steps.append({
                    "time": t,
                    "action_type": "NAVIGATE",
                    "app": app_name,
                    "url": payload.get("url")
                })

        dossier = {
            "case_id": cid,
            "session_id": sid,
            "operator": op,
            "duration_seconds": seg["duration_seconds"],
            "total_raw_events": len(case_evs),
            "action_steps_count": len(action_steps),
            "screenshots_count": len(screenshots_captured),
            "ocr_keyframe_extractions": ocr_texts,
            "action_sequence": action_steps,
            "screenshots_metadata": screenshots_captured[:6]
        }
        case_evidence_dossiers.append(dossier)
        print(f"  [{idx:02d}/{len(selected_cases)}] Extracted Case {cid}: {len(action_steps)} actions, {len(screenshots_captured)} screenshots, {len(ocr_texts)} OCR frames.")

    # Save intermediate evidence JSON
    with open(EVIDENCE_JSON, "w", encoding="utf-8") as ef:
        json.dump(case_evidence_dossiers, ef, ensure_ascii=False, indent=2)
    print(f"\n[Artifact Saved] Raw multimodal evidence persisted to: {EVIDENCE_JSON}")

    # 3. LLM/VLM Workflow Reverse Engineering
    print("\n[Step 4] Prompting LLM/VLM with multimodal event streams and OCR text to induce the complete SOP...")

    # Compact sample for prompt
    prompt_cases_summary = []
    for d in case_evidence_dossiers[:5]:
        sample_actions = []
        for a in d["action_sequence"]:
            if a["action_type"] == "CLICK":
                sample_actions.append(f"CLICK on '{a['target_text']}' in {a['app']} ({a['window_title'][:30]})")
            elif a["action_type"] == "APP_SWITCH":
                sample_actions.append(f"SWITCH to {a['to_app']} ({a['new_title'][:30]})")
            elif a["action_type"] == "CLIPBOARD_PASTE":
                sample_actions.append(f"PASTE clipboard (len={a.get('length')}) into {a['app']}")
            elif a["action_type"] == "KEYSTROKE" and a.get("char") and a.get("char") not in ("None", ""):
                sample_actions.append(f"TYPE '{a['char']}'")
            elif a["action_type"] == "NAVIGATE":
                sample_actions.append(f"NAVIGATE to {a.get('url')}")

        prompt_cases_summary.append({
            "case_id": d["case_id"],
            "operator": d["operator"],
            "duration_s": d["duration_seconds"],
            "ocr_observations": d["ocr_keyframe_extractions"],
            "reconstructed_action_flow": sample_actions[:25]
        })

    sop_prompt = f"""You are a Principal Robotic Process Automation (RPA) and Business Process Architect.
Below is the ground-truth multimodal computer-use telemetry and OCR extractions for 'Invoice Processing' across multiple human operators in an enterprise ERP environment (Microsoft Edge '財務会計システム' + Microsoft Word 'getsujitsu_teigaku_torihikisaki_ichiran [Compatibility Mode]' + Microsoft Excel):

{json.dumps(prompt_cases_summary, ensure_ascii=False, indent=2)}

Task:
Produce a comprehensive, rigorous Standard Operating Procedure (SOP) and Technical Automation Specification for Invoice Processing.

You must detail:
1. Executive Process Summary: Business purpose, frequency, duration, systems involved.
2. Step-by-Step Operator Workflow: Every single phase from discovery to approval.
   - For each step specify:
     * Screen / Window Name
     * Target UI Element (button label, input field placeholder, table cell)
     * Data Source (e.g., Word fixed-vendor transaction list vs Web Portal table)
     * Operator Action (Click, Keystroke, Clipboard Copy/Paste, App Switch)
     * Expected System Response / State Transition
3. Data Dictionary:
   - All data fields involved (Invoice ID, Vendor Code/Name, Voucher Number, Comments, Amounts, Status).
4. Cross-System Data Transfer Logic:
   - Exactly why and when the operator switches between Microsoft Word/Excel and Microsoft Edge, what is copied, and where it is pasted.
5. Decision Logic & Validation Rules:
   - Validation checks performed before clicking 'Approve' (承認).
   - Comment templates (e.g., '処理内容・確認コメント').
6. Edge Cases & Exception Handling:
   - Multi-voucher cases, missing documents, unapproved items.
7. Technical RPA / Automation Blueprint:
   - Target API / Headless Browser / DOM Automation strategy.
   - Required selectors, APIs, payload schemas.
   - Feasibility assessment and potential failure modes.

Format your response in thorough, professional, publication-quality Markdown."""

    llm_sop_markdown = call_llm(sop_prompt)

    # 4. Save Deliverables
    with open(OUTPUT_MD, "w", encoding="utf-8") as mf:
        mf.write(llm_sop_markdown)
    print(f"\n[Deliverable Written] Comprehensive SOP document saved to: {OUTPUT_MD}")

    # Also build a structured JSON summary
    sop_summary_json = {
        "process_name": "Invoice Processing (請求書承認・処理)",
        "analyzed_cases_count": len(selected_cases),
        "total_dataset_b_cases": len(invoice_segments),
        "total_work_minutes": round(sum(s.get("duration_seconds", 0) for s in invoice_segments) / 60.0, 2),
        "systems_involved": ["Microsoft Edge (財務会計システム)", "Microsoft Word", "Microsoft Excel"],
        "sampled_case_ids": [c["case_id"] for c in selected_cases],
        "workflow_steps_overview": [
            "1. Access Financial Accounting System (財務会計システム) Invoice Queue",
            "2. Select Target Invoice Voucher (e.g. INV-2026-XXXX)",
            "3. Cross-System Switch to Vendor Master Document (Word/Excel fixed-rate transaction list)",
            "4. Verify Vendor Code, Line Items, and Monthly Reference Amount",
            "5. Return to ERP Portal & Enter Processing/Confirmation Comment (処理内容・確認コメント)",
            "6. Input / Verify Accounting Voucher Line Code (e.g. P6-XXXXXXXX-XXX)",
            "7. Perform Quantity/Amount Calculation & Verification",
            "8. Click 'Approve' (承認) to Finalize Voucher"
        ]
    }
    with open(OUTPUT_JSON, "w", encoding="utf-8") as jf:
        json.dump(sop_summary_json, jf, ensure_ascii=False, indent=2)
    print(f"[Deliverable Written] Structured SOP JSON saved to: {OUTPUT_JSON}")
    print("\n" + "=" * 90)
    print("INVOICE PROCESSING DEEP-DIVE COMPLETE")
    print("=" * 90)


if __name__ == "__main__":
    main()
