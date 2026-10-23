import requests
import json
import sys
from unified_copilot_erp_app import PAYROLL_PRESET_MEMO

BASE_URL = "http://127.0.0.1:5135"

print("--- Testing GET / ---")
res = requests.get(BASE_URL + "/")
assert res.status_code == 200, f"Expected 200, got {res.status_code}"
html = res.text
assert "global-rule-banner" not in html, "ERROR: global-rule-banner found in HTML!"
assert "toggleLlmOutputCollapse" in html, "ERROR: toggleLlmOutputCollapse not found in HTML!"
assert "runPolicyAnalysis" in html, "ERROR: runPolicyAnalysis not found in HTML!"
assert "continueAndEvaluateDatabase" in html, "ERROR: continueAndEvaluateDatabase not found in HTML!"
assert "extracted-rules-box" in html, "ERROR: extracted-rules-box not found in HTML!"
assert "rules-content-body" in html, "ERROR: rules-content-body not found in HTML!"
print("GET / passed: Global banner removed, collapsible rules UI present, JS functions present.")

print("\n--- Testing POST /api/copilot/analyze (Invoice) ---")
payload_invoice = {
    "process_type": "invoice",
    "document_text": "【月次定額・継続取引先一覧】\n1. Global Tech LLC - 月額 ¥450,000\n2. Nexus Digital - 月額 ¥880,000\n【審査要領】\n- 月次定額取引先は承認とする。\n- 調整金、スポット発注は保留とする。",
    "filename_or_title": "test_invoice_policy.docx"
}
res_analyze_inv = requests.post(BASE_URL + "/api/copilot/analyze", json=payload_invoice)
assert res_analyze_inv.status_code == 200, f"Analyze failed: {res_analyze_inv.text}"
data_inv = res_analyze_inv.json()
assert data_inv.get("success") is True
assert len(data_inv.get("rules", [])) > 0
print(f"Extracted {len(data_inv['rules'])} rules for invoice.")

print("\n--- Testing POST /api/copilot/evaluate with custom_rules ---")
custom_rules = data_inv["rules"]
custom_rules[0]["description"] = "User modified rule description test"
payload_eval = {
    "process_type": "invoice",
    "document_text": payload_invoice["document_text"],
    "filename_or_title": "test_invoice_policy.docx",
    "custom_rules": custom_rules
}
res_eval_inv = requests.post(BASE_URL + "/api/copilot/evaluate", json=payload_eval)
assert res_eval_inv.status_code == 200, f"Evaluate failed: {res_eval_inv.text}"
data_eval = res_eval_inv.json()
assert data_eval.get("success") is True
staged_decisions = data_eval.get("staged_decisions", [])
print(f"Evaluated {len(staged_decisions)} invoice records.")
assert len(staged_decisions) > 0, "No records evaluated!"

# Check first few evaluation comments
for ev in staged_decisions[:3]:
    print(f"ID: {ev.get('id')} | Decision: {ev.get('new_status')} | Comment: {ev.get('comment')}")
    comment = ev.get('comment', '')
    assert any(term in comment for term in ["Verified", "[HOLD]", "Approved", "Monthly", "Policy", "contract", "Recurring"]), f"Comment not in English: {comment}"

print("\n--- Testing POST /api/copilot/analyze (Payroll) ---")
payload_payroll = {
    "process_type": "payroll",
    "document_text": PAYROLL_PRESET_MEMO,
    "filename_or_title": "精算確認メモ.txt"
}
res_analyze_pay = requests.post(BASE_URL + "/api/copilot/analyze", json=payload_payroll)
assert res_analyze_pay.status_code == 200, f"Analyze payroll failed: {res_analyze_pay.text}"
data_pay = res_analyze_pay.json()
assert data_pay.get("success") is True
assert len(data_pay.get("rules", [])) > 0
print(f"Extracted {len(data_pay['rules'])} rules for payroll.")

print("\n--- ALL BACKEND ENDPOINTS AND LOGIC VERIFIED SUCCESSFULLY! ---")
