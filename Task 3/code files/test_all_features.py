import sys
sys.stdout.reconfigure(encoding='utf-8')
import requests, json

BASE = "http://127.0.0.1:5135"

print("--- 1. Testing Home Page (HTML Structure) ---")
r = requests.get(BASE + "/")
assert r.status_code == 200, f"Status code {r.status_code}"
html = r.text
assert "copilot-process-picker" not in html, "copilot-process-picker should be removed"
assert "id=\"schema-info-modal\"" in html, "schema-info-modal should exist"
assert "btn-db-info" in html, "btn-db-info ℹ️ button should exist"
assert "openSchemaInfoModal" in html, "openSchemaInfoModal handler should exist"
assert "id=\"attachment-preview-modal\"" in html, "attachment modal should exist"
print("✓ Home page verified: 3 process cards removed, schema info modal & ℹ️ button present!")

print("--- 2. Testing Database Status ---")
r_db = requests.get(BASE + "/api/database/status")
print("DB Status:", r_db.json())
assert r_db.status_code == 200 and r_db.json().get("connected"), "DB not connected"

print("--- 3. Testing Test-Connection Endpoint ---")
r_ping = requests.post(BASE + "/api/database/test-connection", json={"url": "sqlite"})
print("SQLite Ping:", r_ping.json())
assert r_ping.json().get("success"), "SQLite ping failed"

print("--- 4. Testing Real Account Credits Endpoint ---")
r_cred = requests.get(BASE + "/api/llm/account-credits")
print("Account Credits:", r_cred.json())
assert r_cred.status_code == 200 and r_cred.json().get("success"), "Account credits endpoint failed"
assert "percentage" in r_cred.json() and "display_text" in r_cred.json()

print("--- 5. Testing Windows Explorer Document Opening Endpoint ---")
test_file = "医師診断書_202607.pdf"
r_exp = requests.post(BASE + "/api/open-explorer", json={"filename": test_file, "action": "select"})
print("Explorer Select:", r_exp.json())
assert r_exp.status_code == 200 and r_exp.json().get("file_found"), f"File not found: {test_file}"

print("--- 6. Testing Excel/CSV Upload Schema Validation Flagging ---")
# Upload invalid CSV (missing required columns and non-numeric amount)
invalid_csv = "id,employee_id,name,amount\nINV-999,,ABC,not_a_number\n"
r_val_inv = requests.post(BASE + "/api/upload-table-data", data={"suite": "invoice"}, files={"file": ("test.csv", invalid_csv, "text/csv")})
print("Validation error response (expected 400):", r_val_inv.status_code, r_val_inv.json().get("error"))
assert r_val_inv.status_code == 400 and not r_val_inv.json().get("success")

# Upload valid CSV
valid_csv = "id,employee_id,name,amount,raw_amount\nINV-2026-999,V1001,テスト株式会社,¥500000,500000\n"
r_val_ok = requests.post(BASE + "/api/upload-table-data", data={"suite": "invoice"}, files={"file": ("test.csv", valid_csv, "text/csv")})
print("Validation success response:", r_val_ok.status_code, r_val_ok.json().get("count"), "records")
assert r_val_ok.status_code == 200 and r_val_ok.json().get("count") == 1

print("--- 7. Testing Leave Applications with Document Intelligence ---")
r_leave = requests.get(BASE + "/api/leave-applications")
leave_data = r_leave.json()
print(f"Total Leave Applications: {len(leave_data)}")
assert len(leave_data) == 105
first_att = next(r for r in leave_data if r.get('has_attachment'))
print(f"Applicant: {first_att.get('employee_name')} | Att: {first_att.get('attachment_name')} | HasAtt: {first_att.get('has_attachment')}")
assert first_att.get("attachment_name") is not None

print("\n==========================================")
print("ALL 7 SYSTEM VERIFICATION CHECKS PASSED 100%!")
print("==========================================")
