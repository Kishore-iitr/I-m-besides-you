import os
import json
from tmi_pipeline import PuterLlmClient

os.environ['PUTER_MODEL'] = 'gpt-4o-mini'
client = PuterLlmClient()

sample_doc = """
Monthly Fixed-Price Vendor Policy
1. Yamada Manufacturing Co., Ltd.: ¥385,000
2. Yamato Shoji Co., Ltd.: ¥1,240,000
3. Global Tech LLC: ¥745,000
4. Tokyo Electronics Industry Co., Ltd.: ¥562,800
5. Hokuriku Parts Industry Co., Ltd.: ¥420,000

Policy Rule:
- Approve ONLY if the invoice amount matches the exact contract amount.
- Any mismatch or unregistered vendor must be placed on hold with a specific comment.
- Discrepancy: Any invoice from a listed vendor where the amount differs, or any unlisted vendor.
"""

prompt = f"""
You are a PostgreSQL Expert and Corporate Accounting Auditor.
Convert the following policy document into a valid JSON object containing PostgreSQL SELECT queries to evaluate invoice rows in the table `erp_invoices`.

PostgreSQL Schema:
Table: erp_invoices
Columns:
- id (VARCHAR): Voucher ID (e.g. 'P6-07010448-001')
- name (VARCHAR): Vendor name (e.g. 'Yamada Manufacturing Co., Ltd.')
- invoice_no (VARCHAR): Invoice number (e.g. 'INV-2026-7352')
- raw_amount (INTEGER): Invoiced amount in JPY (e.g. 385000)
- type (VARCHAR): Category ('Routine' or 'Adjustment')
- status (VARCHAR): Status ('Unprocessed', 'Approved', 'On Hold')

Requirements:
1. Provide SQL queries that can be directly executed against PostgreSQL.
2. In 'rules', provide queries to identify which invoices to approve, and which to hold.
3. In 'discrepancy_query', provide a SQL query to identify invoices with amount discrepancies or unregistered vendors that require human intervention.
4. Return ONLY valid JSON.

JSON Structure:
{{
  "policy_title": "string",
  "summary": "string",
  "rules": [
    {{
      "rule_id": "string",
      "rule_name": "string",
      "target_action": "approve" or "hold",
      "comment": "Audit verification note",
      "sql_query": "SELECT id, invoice_no, name, raw_amount FROM erp_invoices WHERE ..."
    }}
  ],
  "discrepancy_query": "SELECT id, invoice_no, name, raw_amount FROM erp_invoices WHERE ...",
  "discrepancy_reason": "string"
}}

Policy Document:
{sample_doc}
"""

res = client.complete_json(prompt)
print(json.dumps(res, indent=2))
