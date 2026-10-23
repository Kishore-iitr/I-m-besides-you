import json
import sys
import time
from pathlib import Path
from tmi_pipeline import PuterLlmClient

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

EVIDENCE_JSON = Path(r"c:\Users\KISHORE S\Desktop\pulled_tmi\payroll_item_multimodal_evidence.json")
with open(EVIDENCE_JSON, "r", encoding="utf-8") as f:
    dossiers = json.load(f)

print(f"Loaded {len(dossiers)} dossiers.")

# Sample 5 distinct duration cases across operators
by_op = {}
for d in dossiers:
    op = d["operator"]
    if op not in by_op:
        by_op[op] = []
    by_op[op].append(d)

sampled = []
for op, cases in by_op.items():
    cases_sorted = sorted(cases, key=lambda x: x["duration_seconds"])
    sampled.append(cases_sorted[0])
    if len(cases_sorted) > 1:
        sampled.append(cases_sorted[-1])

print(f"Sampled {len(sampled)} cases for synthesis:")
for s in sampled:
    print(f"  {s['operator']} | {s['case_id']} | {s['duration_seconds']}s")

prompt_cases_summary = []
for d in sampled:
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
        "reconstructed_action_flow": sample_actions[:30]
    })

prompt_text = f"""You are a Principal Robotic Process Automation (RPA) and Enterprise Business Process Architect.
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

print(f"Prompt length: {len(prompt_text)} characters.")
client = PuterLlmClient(model="gpt-4o-mini")
print("Calling PuterLlmClient...")
t0 = time.time()
res = client.complete(prompt_text, system="You are a lead enterprise workflow architect and RPA specialist.")
print(f"Call finished in {time.time()-t0:.2f}s. Response length: {len(res)} characters.")

with open("PAYROLL_ITEM_PROCESSING_PROCESS_GUIDE.md", "w", encoding="utf-8") as f:
    f.write(res)
print("Saved PAYROLL_ITEM_PROCESSING_PROCESS_GUIDE.md")
