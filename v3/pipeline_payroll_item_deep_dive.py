import sys
import os
import json
import time
import urllib.request
import re
import shutil
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

WORKSPACE_DIR = Path(r"c:\Users\KISHORE S\Desktop\pulled_tmi")
ARTIFACT_DIR = Path(r"C:\Users\KISHORE S\.gemini\antigravity\brain\dfb2d537-2e44-4a91-80fa-976a2105fd5b")

OUTPUT_MD = WORKSPACE_DIR / "PAYROLL_ITEM_PROCESSING_PROCESS_GUIDE.md"
OUTPUT_JSON = WORKSPACE_DIR / "payroll_item_processing_sop.json"
EVIDENCE_JSON = WORKSPACE_DIR / "payroll_item_multimodal_evidence.json"

LOCAL_SCREENSHOTS_DIR = WORKSPACE_DIR / "payroll_item_screenshots"
ARTIFACT_SCREENSHOTS_DIR = ARTIFACT_DIR / "payroll_item_screenshots"
LOCAL_SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

PUTER_TOKEN = os.environ.get(
    "PUTER_AUTH_TOKEN",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6InYyIn0.eyJ0IjoiYXUiLCJ2IjoiMiIsInV1IjoiZ0dXcTBPVE1TdEdSWkZWK2RQZEFWZz09IiwiYXUiOiJKaFNmQzRNRVVpaTVsWGN0cmM5QkRnPT0iLCJzdSI6ImhUS1diTTNnVCtxMHBvVHZpT2JsMUE9PSIsImFpIjoiZ0dXcTBPVE1TdEdSWkZWK2RQZEFWZz09IiwiaWF0IjoxNzkyNTY1OTE4fQ.XrFC2-zDsTcgmO7ioM3kXqu89Wqf48fkFaxZZQs1k1U"
)
PUTER_MODEL = "gpt-4o-mini"
PUTER_URL = "https://api.puter.com/drivers/call"


def call_llm(prompt: str, system_prompt: str = "You are a lead enterprise workflow architect, reverse engineering specialist, and RPA architect.") -> str:
    """Invokes LLM (gpt-4o-mini via Puter API) with automatic retries."""
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
            with urllib.request.urlopen(req, timeout=120) as res:
                data = json.loads(res.read().decode("utf-8"))
                return data.get("result", {}).get("message", {}).get("content", "")
        except Exception as e:
            print(f"[LLM Warning] Attempt {attempt+1} failed: {e}. Retrying in {(attempt+1)*4}s...")
            time.sleep((attempt + 1) * 4)
    return ""


def extract_ocr_from_image(img_path: Path) -> List[str]:
    """Extracts text lines from image using Japanese + English OCR."""
    if not img_path.exists():
        return []
    try:
        img = Image.open(img_path)
        txt = pytesseract.image_to_string(img, lang="jpn+eng")
        lines = [l.strip() for l in txt.splitlines() if len(l.strip()) > 1]
        return lines
    except Exception as e:
        print(f"[OCR Error] {img_path.name}: {e}")
        return []


def main():
    print("=" * 90)
    print("DEDICATED PAYROLL ITEM PROCESSING (RANK 2) DEEP-DIVE & REVERSE-ENGINEERING PIPELINE")
    print(f"Dataset B Path: {DATASET_B_DIR}")
    print(f"Target Output:  {OUTPUT_MD}")
    print("=" * 90)

    # 1. Load recovered segments from Dataset B profiling
    with open(PROFILING_FILE, "r", encoding="utf-8") as pf:
        profiling = json.load(pf)

    all_segments = profiling.get("all_segments_telemetry", [])
    payroll_segments = [s for s in all_segments if "payroll" in s.get("label", "").lower()]
    print(f"[Step 1] Identified {len(payroll_segments)} total payroll processing segments in Dataset B.")

    # Group segments by operator to ensure balanced cross-operator sampling
    by_operator = defaultdict(list)
    for s in payroll_segments:
        by_operator[s.get("operator", "unknown")].append(s)

    selected_cases = []
    # Sample cases from each operator across the duration spectrum
    for op, segs in by_operator.items():
        sorted_segs = sorted(segs, key=lambda x: x.get("duration_seconds", 0))
        if len(sorted_segs) <= 3:
            selected_cases.extend(sorted_segs)
        else:
            selected_cases.append(sorted_segs[0])  # shortest
            selected_cases.append(sorted_segs[len(sorted_segs) // 2])  # median
            selected_cases.append(sorted_segs[-1])  # longest
            # Add one additional representative case if available
            if len(sorted_segs) > 4:
                selected_cases.append(sorted_segs[1])

    print(f"\n[Step 2] Selected {len(selected_cases)} representative cases across {len(by_operator)} operators:")
    for c in selected_cases:
        print(f"  Operator: {c.get('operator'):<16} | Case: {c.get('case_id'):<26} | Dur: {c.get('duration_seconds'):5.1f}s | Label: {c.get('label')}")

    # 2. Extract raw events and screenshots for each selected case
    print("\n[Step 3] Extracting granular action traces, UI elements, and screenshot OCR...")
    case_evidence_dossiers = []
    chunk_events_cache = {}
    copied_screenshots = []

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
                    if img_path.exists():
                        screenshots_captured.append({
                            "filename": fname,
                            "timestamp": t,
                            "trigger": payload.get("trigger_reason"),
                            "app": app_name,
                            "window_title": window_title,
                            "image_path": str(img_path)
                        })

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
                    "action_type": "CLIPBOARD_OP",
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

        # Sample screenshots for OCR & archival (Initial, 25%, 50%, 75%, and End)
        sample_indices = []
        if screenshots_captured:
            n = len(screenshots_captured)
            sample_indices = sorted(list(set([0, n // 4, n // 2, 3 * n // 4, n - 1])))
            for s_idx in sample_indices:
                sc = screenshots_captured[s_idx]
                src_p = Path(sc["image_path"])
                dest_name = f"{cid}_{sc['filename']}"
                dest_local = LOCAL_SCREENSHOTS_DIR / dest_name
                dest_art = ARTIFACT_SCREENSHOTS_DIR / dest_name
                
                try:
                    if not dest_local.exists():
                        shutil.copy2(src_p, dest_local)
                    if not dest_art.exists():
                        shutil.copy2(src_p, dest_art)
                    copied_screenshots.append(str(dest_local))
                except Exception as ex:
                    pass

                # Run OCR
                lines = extract_ocr_from_image(src_p)
                ocr_texts[sc["filename"]] = lines[:20]

        dossier = {
            "case_id": cid,
            "session_id": sid,
            "operator": op,
            "label": seg.get("label"),
            "duration_seconds": seg["duration_seconds"],
            "total_raw_events": len(case_evs),
            "action_steps_count": len(action_steps),
            "screenshots_count": len(screenshots_captured),
            "ocr_keyframe_extractions": ocr_texts,
            "action_sequence": action_steps,
            "screenshots_metadata": screenshots_captured[:8]
        }
        case_evidence_dossiers.append(dossier)
        print(f"  [{idx:02d}/{len(selected_cases)}] Extracted Case {cid} ({op}): {len(action_steps)} actions, {len(screenshots_captured)} screenshots, {len(ocr_texts)} OCR frames.")

    # Save intermediate multimodal evidence JSON
    with open(EVIDENCE_JSON, "w", encoding="utf-8") as ef:
        json.dump(case_evidence_dossiers, ef, ensure_ascii=False, indent=2)
    print(f"\n[Artifact Saved] Raw multimodal evidence persisted to: {EVIDENCE_JSON}")
    print(f"[Artifact Saved] Keyframe screenshots copied to: {LOCAL_SCREENSHOTS_DIR} and {ARTIFACT_SCREENSHOTS_DIR}")

    # 3. LLM Reverse-Engineering Prompting
    print("\n[Step 4] Prompting LLM (gpt-4o-mini) with multimodal event streams and OCR text to reverse-engineer the complete SOP...")

    # Compact sample for LLM synthesis
    prompt_cases_summary = []
    for d in case_evidence_dossiers:
        sample_actions = []
        for a in d["action_sequence"]:
            if a["action_type"] == "CLICK":
                sample_actions.append(f"CLICK on '{a['target_text']}' in {a['app']} ({a['window_title'][:30]})")
            elif a["action_type"] == "APP_SWITCH":
                sample_actions.append(f"SWITCH {a['from_app']} -> {a['to_app']} ({a['new_title'][:30]})")
            elif a["action_type"] == "CLIPBOARD_OP":
                sample_actions.append(f"CLIPBOARD operation (len={a.get('length')}, fmts={a.get('formats')}) in {a['app']}")
            elif a["action_type"] == "KEYSTROKE" and a.get("char") and a.get("char") not in ("None", ""):
                sample_actions.append(f"TYPE '{a['char']}'")
            elif a["action_type"] == "NAVIGATE":
                sample_actions.append(f"NAVIGATE to {a.get('url')}")

        prompt_cases_summary.append({
            "case_id": d["case_id"],
            "operator": d["operator"],
            "label": d.get("label"),
            "duration_s": d["duration_seconds"],
            "ocr_observations": d["ocr_keyframe_extractions"],
            "reconstructed_action_flow": sample_actions[:35]
        })

    sop_prompt = f"""You are a Principal Robotic Process Automation (RPA) and Enterprise Business Process Architect.
Below is the ground-truth multimodal computer-use telemetry and OCR extractions for Rank 2 Automation Candidate: 'Payroll Item Processing' (給与備考・控除・経費整備 / payroll_item_processing) across multiple human operators (NEELA9BAF, LAPTOP-76QMG9DE, CHAITANYA0BCF) in an enterprise ERP environment.

Systems Involved:
- Microsoft Edge: 'HR人事給与システム' (HR & Payroll ERP System, route `#/payroll-items`, ports 5132/5134)
- Notepad: '*精算確認メモ' (Expense Reimbursement Confirmation Memo), '*在庫調整メモ'
- Microsoft Word: 'gyomu_itaku_keihi_kitei' (Outsourcing Expense Regulations), 'gyomu_itaku_kyuuyo_kitei' (Payroll Regulations), 'gyomu_itaku_ukeire_tetsuzuki' (Acceptance Procedures)
- Microsoft Excel: Supplementary payroll registers

Multimodal Case Telemetry & OCR Observations:
{json.dumps(prompt_cases_summary, ensure_ascii=False, indent=2)}

Task:
Produce a comprehensive, rigorous, publication-quality Standard Operating Procedure (SOP) and Technical Automation Specification for Payroll Item Processing.

You must cover the following 7 Core Sections in meticulous detail:

# Standard Operating Procedure (SOP): Payroll Item Processing & Deduction Reconciliation (給与備考・控除整備)

1. Executive Process Summary:
   - Business Purpose & Scope: Explain the operational goal of payroll item processing (expense reimbursements, allowance adjustments, base salary revisions, dependent deductions).
   - Volume, Frequency & Criticality: Frequency (monthly payroll cutoff cycle), duration metrics (24s - 203s per batch/case, mean ~79.4s), business risk of payroll inaccuracies.
   - Core Systems & Architecture: Microsoft Edge (HR人事給与システム `#/payroll-items`), Notepad (`*精算確認メモ`), Microsoft Word regulations.

2. End-to-End Step-by-Step Operator Workflow:
   - Phase 1: Intake & Reference Document Discovery (opening Notepad `*精算確認メモ` and Word policy documents).
   - Phase 2: Navigation to HR & Payroll Portal (accessing `#/payroll-items` queue, selecting employee / batch record).
   - Phase 3: Expense / Allowance Category Selection (clicking items such as `消耗品費`, `研修費`, `出張旅費`, `交通費精算`, `接待交際費`, `残業手当調整`, `昇給`, `扶養控除変更`, `役職手当新設`, `役職手当廃止`).
   - Phase 4: Cross-Application Clipboard Transfer & Comment Entry (copying structured confirmation notes from Notepad/Word and pasting into placeholder `処理内容・確認コメントを入力してください…`).
   - Phase 5: Voucher & Allocation ID Linking (selecting voucher code such as `P4-07089771-012`, `P4-07054374-012`, `P1-07089771-008`).
   - Phase 6: Final Verification, Amount Confirmation & Approval (saving line item and batch confirmation).
   - Provide a step table detailing: Step # | Window / Screen | Target UI Element (exact Japanese text & CSS/XPath) | Operator Action | Data Source | Expected System Response.

3. Complete Data Dictionary:
   - Tabulate all business entities, codes, fields, and structures:
     * Employee ID & Name (e.g., 石田 美奈, 菊池 理恵, 坂本 裕二, 青木 拓也, 桐島 涼介, 江口 さくら, 島田 奈々)
     * Voucher / Allocation ID syntax (e.g., `P4-07089771-012`, `P7-07089771-001`, `P10-07047510-012`)
     * Item Categories (Additions vs. Deductions vs. Expense Reimbursements)
     * Confirmation Comments syntax & standard templates (e.g., '経費精算確認済み。 研修費 金額: XX,XXX円。 規程内であることを確認した。')
     * Monetary Amounts & Tax implications.

4. Cross-System Data Transfer Logic:
   - Detailed mapping of the clipboard bridge between Notepad/Word and Edge ERP.
   - Analysis of clipboard payloads (lengths 35-66 chars) and how unstructured text in memos maps to structured form inputs in the ERP.

5. Business Rules, Validation Matrix & Decision Logic:
   - Validation criteria before approving any payroll item (amount limits per category, expense policy compliance, voucher code format).
   - Decision table for handling discrepancies (e.g., amount exceeding regulation threshold, mismatched voucher ID, invalid employee status).

6. Edge Cases & Exception Handling:
   - Handling multi-item reimbursement batches (BATCH-W1 to BATCH-W6).
   - Handling unrecognized voucher codes or missing receipt memos.
   - Handling negative adjustments (deductions vs additions).
   - Human escalation protocols when policy limits are breached.

7. Technical RPA & Headless Automation Blueprint:
   - System Architecture: Target API endpoints vs Headless Playwright / Puppeteer browser automation.
   - DOM Selectors, Element Locators, and Event Triggers for `HR人事給与システム`.
   - Data Flow Diagram (Mermaid sequence/flowchart).
   - Security, Audit Trail, and Governance compliance.

Format your output in professional, publication-quality GitHub-flavored Markdown."""

    llm_sop_markdown = call_llm(sop_prompt)

    # 4. Save Deliverables
    with open(OUTPUT_MD, "w", encoding="utf-8") as mf:
        mf.write(llm_sop_markdown)
    print(f"\n[Deliverable Written] Comprehensive SOP document saved to: {OUTPUT_MD}")

    # Build structured JSON summary
    sop_summary_json = {
        "process_name": "Payroll Item Processing (給与備考・控除・経費整備)",
        "candidate_rank": 2,
        "automation_priority_score": 19.12,
        "automation_suitability_index": 85.0,
        "analyzed_cases_count": len(selected_cases),
        "total_dataset_b_cases": len(payroll_segments),
        "total_work_minutes": round(sum(s.get("duration_seconds", 0) for s in payroll_segments) / 60.0, 2),
        "operators_involved": list(by_operator.keys()),
        "systems_involved": [
            "Microsoft Edge (HR人事給与システム `#/payroll-items`)",
            "Notepad (*精算確認メモ / *在庫調整メモ)",
            "Microsoft Word (gyomu_itaku_keihi_kitei / gyomu_itaku_kyuuyo_kitei)",
            "Microsoft Excel (Supplementary payroll registers)"
        ],
        "sampled_case_ids": [c["case_id"] for c in selected_cases],
        "key_payroll_items": [
            "消耗品費 (Consumables Expense)",
            "研修費 (Training Expense)",
            "出張旅費 (Business Travel Expense)",
            "交通費精算 (Transportation Expense Settlement)",
            "接待交際費 (Entertainment Expense)",
            "残業手当調整 (Overtime Allowance Adjustment)",
            "昇給 (Base Salary Raise)",
            "扶養控除変更 (Dependent Deduction Modification)",
            "役職手当新設 (Executive Allowance Addition)",
            "役職手当廃止 (Executive Allowance Abolition)"
        ],
        "workflow_steps_overview": [
            "1. Intake & Reference Discovery: Open Notepad `*精算確認メモ` and Word expense regulations",
            "2. Access HR & Payroll Portal: Open Microsoft Edge `HR人事給与システム` on route `#/payroll-items`",
            "3. Select Target Employee / Batch Voucher: Locate employee record (e.g., 青木 拓也, 菊池 理恵)",
            "4. Select Expense / Deduction Item Category: Click target category button (e.g. 研修費, 消耗品費, 残業手当調整)",
            "5. Copy Confirmation Note: Extract verified comment from Notepad memo (`経費精算確認済み。 [Category] 金額: [Amount]円。 規程内であることを確認した。`)",
            "6. Input / Paste Confirmation Details: Paste into input field `処理内容・確認コメントを入力してください…`",
            "7. Link Voucher Code: Click / assign corresponding voucher ID (e.g. `P4-07089771-012`)",
            "8. Verify & Finalize: Review line item calculations and commit batch approval to update payroll register"
        ]
    }
    with open(OUTPUT_JSON, "w", encoding="utf-8") as jf:
        json.dump(sop_summary_json, jf, ensure_ascii=False, indent=2)
    print(f"[Deliverable Written] Structured SOP JSON saved to: {OUTPUT_JSON}")
    print("\n" + "=" * 90)
    print("RANK 2 CANDIDATE (PAYROLL ITEM PROCESSING) DEEP-DIVE COMPLETE")
    print("=" * 90)


if __name__ == "__main__":
    main()
