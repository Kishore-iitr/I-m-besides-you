import json
from tmi_pipeline import PuterLlmClient
from erp_db import db_manager

# Get current distinct invoices from the PostgreSQL database
invoices = db_manager.fetch_all()
db_context = [{"id": inv["id"], "name": inv["name"], "raw_amount": inv["raw_amount"], "type": inv["type"], "invoice_no": inv["invoice_no"]} for inv in invoices]

sample_doc = """
IT Services & Logistics Provider Audit Policy 2026
Scope: IT Contractors and Logistics Freight Suppliers

Rules:
1. IT Systems Engineering (Fukuoka System Design):
   - Approved if monthly invoice is under ¥2,000,000 for milestone delivery.
   - If ¥2,000,000 or greater, put on hold for CTO sign-off.
2. Logistics Operations (Okinawa Logistics Center):
   - Approved if category is Adjustment and billing is under ¥500,000.
   - Other logistics invoices over ¥500,000 are on hold.
3. Component Manufacturing (Hokuriku Parts Industry Co., Ltd.):
   - Adjustment category must be held pending Quality Inspection Report.
4. Other Vendors:
   - Routine hardware/parts suppliers (such as Yamada, Yamato) are out of scope for this policy and must be held for standard accounting review.
"""

prompt = f"""
You are an expert PostgreSQL Database Architect and Enterprise Financial Auditor.
Analyze the following corporate policy document and dynamically synthesize executable PostgreSQL queries to evaluate invoices in `erp_invoices`.

PostgreSQL Table: `erp_invoices`
Columns:
- id (VARCHAR): Unique invoice ID
- name (VARCHAR): Vendor Name
- invoice_no (VARCHAR): Invoice Number
- raw_amount (INTEGER): Invoiced amount in JPY
- type (VARCHAR): Category ('Routine' or 'Adjustment')
- status (VARCHAR): 'Unprocessed', 'Approved', 'On Hold'

Current invoices in the database:
{json.dumps(db_context, indent=2, ensure_ascii=False)}

Policy Document:
{sample_doc}

Generate a valid JSON object with the following structure:
{{
  "policy_title": "Title extracted from document",
  "summary": "1-2 sentence summary of extracted business logic",
  "rules": [
    {{
      "rule_id": "rule_1",
      "rule_name": "Descriptive rule name",
      "target_action": "approve" or "hold",
      "comment": "Audit note to record on the invoice",
      "sql_query": "SELECT id FROM erp_invoices WHERE ..."
    }}
  ],
  "discrepancy_query": "SELECT id FROM erp_invoices WHERE ...",
  "discrepancy_reason": "Explanation of discrepancies requiring human review"
}}

Return ONLY valid JSON.
"""

client = PuterLlmClient(model="gpt-4o-mini")
res = client.complete_json(prompt)
print(json.dumps(res, indent=2))
