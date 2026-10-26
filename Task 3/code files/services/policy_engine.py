# -*- coding: utf-8 -*-
# File: services/policy_engine.py
# Description: Enterprise Policy-to-SQL Extraction, Validation, Evaluation, and Staging Engine.
# Replicates the exact verified copilot architecture with Puter LLM and safe PostgreSQL execution.

import os
import re
import time
import json
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from pathlib import Path

from config.database import DB_CONFIG
from services.puter_client import PuterLlmClient, clean_and_parse_json_robust
import psycopg2
from psycopg2.extras import DictCursor


# ==============================================================================
# SCHEMA METADATA WITH DATA TYPES & DESCRIPTIONS
# ==============================================================================
TABLE_SCHEMAS = {
    "erp_invoices": {
        "description": "Accounts Payable Invoices table storing vendor billing and payment vouchers (No employee ID; features vendor code, vendor name, invoice number, category, and monetary amount).",
        "target_status_column": "status",
        "allowed_statuses": ["Unprocessed", "Approved", "Hold"],
        "columns": {
            "id": {"type": "VARCHAR", "description": "Unique invoice voucher ID (e.g. 'P6-07010448-001')"},
            "vendor_code": {"type": "VARCHAR", "description": "Vendor Code / 取引先コード (e.g. 'V3001'..'V3012'; unregistered: 'V3099'). NEVER use employee_id!"},
            "vendor_name": {"type": "VARCHAR", "description": "Vendor Name / 取引先企業名 (e.g. 'Global Tech LLC', '北陸部品工業株式会社')"},
            "invoice_no": {"type": "VARCHAR", "description": "Vendor external invoice reference number (e.g. 'INV-2026-7353')"},
            "type": {"type": "VARCHAR", "description": "Invoice classification / 区分 ('Routine' or 'Adjustment')"},
            "amount": {"type": "VARCHAR", "description": "Formatted monetary string with symbol (e.g. '¥716,232')"},
            "raw_amount": {"type": "BIGINT", "description": "Numeric transaction amount in JPY without symbols or commas (e.g. 716232, 1500000)"},
            "status": {"type": "VARCHAR", "description": "Target approval status ('Unprocessed', 'Approved', 'Hold')"},
            "comment": {"type": "TEXT", "description": "Audit trail comment detailing compliance/hold rationale"}
        }
    },
    "erp_payroll_items": {
        "description": "Employee Payroll & Expense Settlements table storing reimbursements, allowances, and deductions (Features employee ID, employee name, expense category, item type, and amount).",
        "target_status_column": "status",
        "allowed_statuses": ["Unprocessed", "Approved", "Confirmed", "Hold"],
        "columns": {
            "id": {"type": "VARCHAR", "description": "Unique voucher ID (e.g. 'P4-07089771-001')"},
            "employee_id": {"type": "VARCHAR", "description": "Employee ID / 従業員コード (e.g. 'EMP-001', 'EMP-002')"},
            "employee_name": {"type": "VARCHAR", "description": "Employee legal full name / 従業員氏名 (e.g. '青木 拓也', '菊地 里江')"},
            "item_category": {"type": "VARCHAR", "description": "Expense or allowance category / 項目名 (e.g. '研修費', '消耗品費', '出張旅費', '交通費精算', '残業手当調整', '接待交際費', '資格取得手当', '扶養控除変更', '役職手当廃止', '未登録手当')"},
            "item_type": {"type": "VARCHAR", "description": "Payment classification ('Addition' = 支給/加算, 'Deduction' = 控除/減算)"},
            "amount": {"type": "VARCHAR", "description": "Formatted monetary amount string (e.g. '¥77,224')"},
            "raw_amount": {"type": "BIGINT", "description": "Numeric integer transaction amount in JPY without formatting (e.g. 77224, 150000)"},
            "voucher_ref": {"type": "VARCHAR", "description": "Reference voucher ID (e.g. 'P1-07089771-008')"},
            "status": {"type": "VARCHAR", "description": "Target status ('Unprocessed', 'Approved', 'Confirmed', 'Hold')"},
            "comment": {"type": "TEXT", "description": "Audit trail comment detailing compliance/hold rationale"}
        }
    },
    "erp_leave_applications": {
        "description": "Employee Leave Applications & Time-Off Management table storing annual, special, bereavement, and medical leave requests (Features employee ID, employee name, department, leave type, start/end dates, requested days, remaining balance, reason, attachment status, and attachment name).",
        "target_status_column": "status",
        "allowed_statuses": ["Unprocessed", "Approved", "Hold"],
        "columns": {
            "id": {"type": "VARCHAR", "description": "Unique leave request ID (e.g. 'LV-2026-001')"},
            "employee_id": {"type": "VARCHAR", "description": "Employee ID / 従業員コード (e.g. 'EMP-001'..'EMP-030')"},
            "employee_name": {"type": "VARCHAR", "description": "Employee full name / 従業員氏名 (e.g. '青木 拓也')"},
            "department": {"type": "VARCHAR", "description": "Department name / 所属部署 (e.g. '第一開発部', '営業統括部', '総務人事部', '経理財務部', 'カスタマーサポート部')"},
            "leave_type": {"type": "VARCHAR", "description": "Leave classification / 休暇種別 ('有給休暇', '半日有給申請', '慶弔特別休暇', '病気休暇', '夏季特別休暇', '在宅研修休暇', '未登録休暇')"},
            "start_date": {"type": "VARCHAR", "description": "Leave start date string (e.g. '2026-08-03')"},
            "end_date": {"type": "VARCHAR", "description": "Leave end date string (e.g. '2026-08-05')"},
            "requested_days": {"type": "NUMERIC", "description": "Number of days requested (e.g. 0.5, 1.0, 2.0, 3.0, 5.0, 7.0)"},
            "remaining_balance": {"type": "NUMERIC", "description": "Remaining paid leave quota in days before this request (e.g. 0.0, 1.5, 5.0, 14.5)"},
            "reason": {"type": "TEXT", "description": "Reason for leave / 申請事由"},
            "has_attachment": {"type": "BOOLEAN", "description": "Whether supporting document is attached (TRUE / FALSE)"},
            "attachment_name": {"type": "VARCHAR", "description": "Supporting file attachment name (e.g. '医師診断書_202607.pdf', '会葬礼状_写し.pdf')"},
            "voucher_ref": {"type": "VARCHAR", "description": "Reference tracking code (e.g. 'P2-07101496-012')"},
            "status": {"type": "VARCHAR", "description": "Target approval status ('Unprocessed', 'Approved', 'Hold')"},
            "comment": {"type": "TEXT", "description": "Audit trail comment detailing review rationale"}
        }
    }
}


def make_sql_case_insensitive(cond: str, table_name: str = "erp_invoices") -> str:
    """Transforms SQL conditions on text columns to be case-insensitive in ANSI SQL."""
    if table_name == "erp_invoices":
        text_cols_upper = ['vendor_code', 'id', 'invoice_no']
        text_cols_lower = ['type', 'vendor_name', 'name', 'status']
    elif table_name == "erp_leave_applications":
        text_cols_upper = ['employee_id', 'id', 'voucher_ref']
        text_cols_lower = ['department', 'leave_type', 'employee_name', 'status', 'attachment_name', 'reason']
    else:
        text_cols_upper = ['employee_id', 'id', 'voucher_ref']
        text_cols_lower = ['item_category', 'item_type', 'employee_name', 'status']

    result = cond

    for col in text_cols_upper:
        def repl_in(m):
            op = m.group(1)
            inner = m.group(2).strip()
            if "select" in inner.lower():
                return f"UPPER({col}) {op} ({inner})"
            upper_items = re.sub(r"'([^']*)'", lambda sm: f"'{sm.group(1).upper()}'", inner)
            return f"UPPER({col}) {op} ({upper_items})"
        pattern = rf"(?<![A-Za-z0-9_]){col}\s+(IN|NOT\s+IN)\s*\((.*?)\)"
        result = re.sub(pattern, repl_in, result, flags=re.IGNORECASE)

        def repl_eq(m):
            op = m.group(1)
            val = m.group(2)
            return f"UPPER({col}) {op} '{val.upper()}'"
        pattern_eq = rf"(?<![A-Za-z0-9_]){col}\s*([!=<>]+)\s*'([^']*)'"
        result = re.sub(pattern_eq, repl_eq, result, flags=re.IGNORECASE)

    for col in text_cols_lower:
        def repl_in(m):
            op = m.group(1)
            inner = m.group(2).strip()
            if "select" in inner.lower():
                return f"LOWER({col}) {op} ({inner})"
            lower_items = re.sub(r"'([^']*)'", lambda sm: f"'{sm.group(1).lower()}'", inner)
            return f"LOWER({col}) {op} ({lower_items})"
        pattern = rf"(?<![A-Za-z0-9_]){col}\s+(IN|NOT\s+IN)\s*\((.*?)\)"
        result = re.sub(pattern, repl_in, result, flags=re.IGNORECASE)

        def repl_eq(m):
            op = m.group(1)
            val = m.group(2)
            return f"LOWER({col}) {op} '{val.lower()}'"
        pattern_eq = rf"(?<![A-Za-z0-9_]){col}\s*([!=<>]+)\s*'([^']*)'"
        result = re.sub(pattern_eq, repl_eq, result, flags=re.IGNORECASE)

    return result


def evaluate_sql_condition_in_memory(row: dict, sql_cond: str) -> bool:
    """Evaluates an ANSI SQL WHERE condition against a dictionary row in Python with case-insensitivity."""
    cond = str(sql_cond or "").strip()
    if not cond:
        return True

    if not row.get("vendor_code") and row.get("employee_id"):
        row["vendor_code"] = row["employee_id"]
    if not row.get("vendor_name") and row.get("name"):
        row["vendor_name"] = row["name"]
    if not row.get("name") and row.get("vendor_name"):
        row["name"] = row["vendor_name"]
    if not row.get("customer_name") and (row.get("vendor_name") or row.get("name")):
        row["customer_name"] = row.get("vendor_name") or row.get("name")
    if not row.get("employee_id") and row.get("vendor_code"):
        row["employee_id"] = row["vendor_code"]
    if "type" in row and row["type"]:
        row["type"] = str(row["type"])

    def _to_clean_str(val):
        if val is None:
            return ""
        return str(val).strip().lower()

    def _case_eq(a, b):
        return _to_clean_str(a) == _to_clean_str(b)

    def _case_in(val, items):
        v = _to_clean_str(val)
        return any(v == _to_clean_str(i) for i in items)

    def _case_not_in(val, items):
        v = _to_clean_str(val)
        return not any(v == _to_clean_str(i) for i in items)

    transformed = cond
    transformed = re.sub(r'\bAND\b', ' and ', transformed, flags=re.IGNORECASE)
    transformed = re.sub(r'\bOR\b', ' or ', transformed, flags=re.IGNORECASE)
    transformed = re.sub(r'\bNOT\b', ' not ', transformed, flags=re.IGNORECASE)
    transformed = re.sub(r'(?<![!=<>])=(?!=)', '==', transformed)

    def replace_not_in(match):
        col = match.group(1).strip()
        items_raw = match.group(2)
        items = [i.strip().strip("'\"") for i in items_raw.split(',') if i.strip()]
        return f"_case_not_in(row.get('{col}'), {items})"

    def replace_in(match):
        col = match.group(1).strip()
        items_raw = match.group(2)
        items = [i.strip().strip("'\"") for i in items_raw.split(',') if i.strip()]
        return f"_case_in(row.get('{col}'), {items})"

    transformed = re.sub(r'([A-Za-z0-9_]+)\s+not\s+in\s*\((.*?)\)', replace_not_in, transformed, flags=re.IGNORECASE)
    transformed = re.sub(r'([A-Za-z0-9_]+)\s+in\s*\((.*?)\)', replace_in, transformed, flags=re.IGNORECASE)

    def replace_eq(match):
        col = match.group(1).strip()
        op = match.group(2).strip()
        val = match.group(3).strip().strip("'\"")
        if op == '==':
            return f"_case_eq(row.get('{col}'), '{val}')"
        elif op == '!=':
            return f"(not _case_eq(row.get('{col}'), '{val}'))"
        return match.group(0)

    transformed = re.sub(r'([A-Za-z0-9_]+)\s*(==|!=)\s*\'([^\']*)\'', replace_eq, transformed)

    # Normalize SQL boolean and IS operators
    transformed = re.sub(r'\bIS\s+TRUE\b', '== True', transformed, flags=re.IGNORECASE)
    transformed = re.sub(r'\bIS\s+FALSE\b', '== False', transformed, flags=re.IGNORECASE)
    transformed = re.sub(r'\bIS\s+NOT\s+TRUE\b', '!= True', transformed, flags=re.IGNORECASE)
    transformed = re.sub(r'\bIS\s+NOT\s+FALSE\b', '!= False', transformed, flags=re.IGNORECASE)
    transformed = re.sub(r'\bIS\s+NULL\b', 'is None', transformed, flags=re.IGNORECASE)
    transformed = re.sub(r'\bIS\s+NOT\s+NULL\b', 'is not None', transformed, flags=re.IGNORECASE)

    eval_globals = {
        "__builtins__": None,
        "_case_eq": _case_eq,
        "_case_in": _case_in,
        "_case_not_in": _case_not_in,
        "true": True,
        "false": False,
        "True": True,
        "False": False,
        "null": None,
        "NULL": None,
    }
    eval_locals = {"row": row}

    for col in row.keys():
        transformed = re.sub(rf'\b{col}\b(?!\s*[\'\"\(])', f"row.get('{col}')", transformed)

    try:
        return bool(eval(transformed, eval_globals, eval_locals))
    except Exception:
        return False


class PolicyEngine:
    """Core enterprise policy rule extraction, verification, staging, and DB execution engine."""

    def __init__(self, puter_client: Optional[PuterLlmClient] = None):
        self.llm = puter_client or PuterLlmClient()

    def get_connection(self):
        """Creates a PostgreSQL connection using DB_CONFIG with fallback to db_manager."""
        try:
            from erp_db import db_manager
            return db_manager.get_connection()
        except Exception:
            return psycopg2.connect(**DB_CONFIG, cursor_factory=DictCursor)

    def fetch_all_rows(self, table_name: str, conn: Optional[Any] = None) -> List[Dict[str, Any]]:
        """Fetches all rows from the target table."""
        def _to_dicts(cursor):
            col_names = [d[0] for d in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            result = []
            for r in rows:
                if isinstance(r, dict):
                    result.append(dict(r))
                elif hasattr(r, "_asdict"):
                    result.append(r._asdict())
                elif hasattr(r, "keys"):
                    result.append(dict(r))
                else:
                    result.append(dict(zip(col_names, r)))
            return result

        if conn is not None:
            with conn.cursor() as cur:
                cur.execute(f"SELECT * FROM {table_name} ORDER BY id ASC;")
                return _to_dicts(cur)
        with self.get_connection() as c:
            with c.cursor() as cur:
                cur.execute(f"SELECT * FROM {table_name} ORDER BY id ASC;")
                return _to_dicts(cur)

    def query_matching_ids(self, table_name: str, sql_cond: str, conn: Optional[Any] = None) -> Optional[Set[str]]:
        """Executes a SQL WHERE condition against the live PostgreSQL database."""
        if not sql_cond or not sql_cond.strip():
            return None
        clean_cond = sql_cond.strip().rstrip(';')
        normalized_cond = make_sql_case_insensitive(clean_cond, table_name)
        try:
            if conn is not None:
                with conn.cursor() as cur:
                    query = f"SELECT id FROM {table_name} WHERE ({normalized_cond});"
                    cur.execute(query)
                    rows = cur.fetchall()
                    return {str(r[0]) for r in rows if r and r[0] is not None}
            conn_obj = self.get_connection()
            try:
                cur = conn_obj.cursor()
                query = f"SELECT id FROM {table_name} WHERE ({normalized_cond});"
                cur.execute(query)
                rows = cur.fetchall()
                return {str(r[0]) for r in rows if r and r[0] is not None}
            finally:
                try:
                    conn_obj.close()
                except Exception:
                    pass
        except Exception as e:
            logging.warning(f"[Live SQL Query Error] {e} on condition: {normalized_cond}")
            return None

    # --- Node 1: Extract Policy Rules ---
    def extract_policy_rules(self, process_type: str, policy_text: str) -> List[Dict[str, Any]]:
        """Grounds LLM in table schema and extracts Rule ID, Target/Entity, SQL Logic (SL), and Action."""
        if process_type in ("leave", "leave_mgmt", "leave_applications"):
            table_name = "erp_leave_applications"
        elif process_type == "payroll":
            table_name = "erp_payroll_items"
        else:
            table_name = "erp_invoices"
        schema_info = TABLE_SCHEMAS.get(table_name, {})

        if process_type in ("leave", "leave_mgmt", "leave_applications"):
            system_prompt = (
                "You are an Elite Enterprise Database & Policy Rule Extraction Agent specializing in Employee Leave Applications & Attendance Management (erp_leave_applications).\n"
                "CRITICAL SCHEMA & DATA TYPE SPECIFICATIONS FOR erp_leave_applications:\n"
                "1. DATABASE COLUMNS IN erp_leave_applications:\n"
                "   - `employee_id` (VARCHAR): Employee code (e.g. 'EMP-001', 'EMP-002').\n"
                "   - `employee_name` (VARCHAR): Employee legal full name (e.g. '青木 拓也', '菊池 理恵').\n"
                "   - `department` (VARCHAR): Department name (e.g. '開発部', '総務部', '営業部', '経理部', 'カスタマーサポート').\n"
                "   - `leave_type` (VARCHAR): Leave type ('有給休暇', '半日有給申請', '慶弔特別休暇', '病気休暇', '夏季特別休暇', '在宅研修休暇', '未登録休暇').\n"
                "   - `requested_days` (NUMERIC): Number of days requested (e.g. 0.5, 1.0, 2.0, 3.0, 5.0, 7.0). ALWAYS numeric comparison!\n"
                "   - `remaining_balance` (NUMERIC): Remaining leave quota in days before this request (e.g. 0.0, 1.0, 12.0, 14.5).\n"
                "   - `has_attachment` (BOOLEAN): Supporting certificate/proof attached (TRUE or FALSE).\n"
                "   - `attachment_name` (VARCHAR): Attachment filename (e.g. '医師診断書_202607.pdf').\n"
                "   - `voucher_ref` (VARCHAR): Linked voucher/reference ID (e.g. 'P2-07101496-012').\n"
                "2. PRECISE SQL MAPPINGS FOR LEAVE POLICIES:\n"
                "   - Quota deficit hold (requested > remaining): sql_condition: \"requested_days > remaining_balance\", action_on_match: \"Hold\"\n"
                "   - Consecutive long leave threshold (>3 days or >5 days requires approval): sql_condition: \"requested_days > 3.0\", action_on_match: \"Hold\"\n"
                "   - Medical leave without doctor's certificate: sql_condition: \"leave_type = '病気休暇' AND has_attachment = FALSE\", action_on_match: \"Hold\"\n"
                "   - Special bereavement leave missing documentation: sql_condition: \"leave_type = '慶弔特別休暇' AND has_attachment = FALSE\", action_on_match: \"Hold\"\n"
                "   - Unregistered leave category: sql_condition: \"leave_type = '未登録休暇'\", action_on_match: \"Hold\"\n"
                "   - Approved standard leave: sql_condition: \"leave_type IN ('有給休暇', '半日有給申請', '夏季特別休暇', '在宅研修休暇') AND requested_days <= remaining_balance AND requested_days <= 3.0\", action_on_match: \"Approved\"\n"
                "3. REQUIRED JSON FIELDS FOR EVERY RULE:\n"
                "   - \"rule_id\": e.g. \"RULE-LV-01\"\n"
                "   - \"name\": Concise descriptive rule title\n"
                "   - \"match_field\": Primary column checked (e.g. \"requested_days\", \"leave_type\", \"has_attachment\")\n"
                "   - \"match_value\": Target or entity label\n"
                "   - \"sql_condition\": Valid ANSI SQL predicate against erp_leave_applications\n"
                "   - \"condition\": Same as sql_condition\n"
                "   - \"action_on_match\": \"Hold\" or \"Approved\"\n"
                "   - \"description\": Professional explanation\n"
            )
            prompt = f"""Target Process: LEAVE_APPLICATIONS
Target Database Table: {table_name}
Target Table Schema:
{json.dumps(schema_info, indent=2, ensure_ascii=False)}

Incoming Document / Policy Text:
\"\"\"{policy_text}\"\"\"

Instructions:
1. Extract ALL rules: quota sufficiency, consecutive day limits, required medical/bereavement attachments, unregistered leave codes, and standard approved leave categories.
2. For EVERY rule, generate a valid SQL WHERE condition (`sql_condition` and `condition`) against `{table_name}`.
3. Every rule MUST include: `rule_id`, `name`, `match_field`, `match_value`, `sql_condition`, `condition`, `action_on_match` ("Hold" or "Approved"), and `description`.
4. Return ONLY valid JSON with key "item_criteria" without markdown fences."""
        elif process_type == "payroll":
            system_prompt = (
                "You are an Elite Enterprise Database & Policy Rule Extraction Agent specializing in Employee Payroll Expense Settlements (erp_payroll_items).\n"
                "CRITICAL SCHEMA & DATA TYPE SPECIFICATIONS FOR erp_payroll_items:\n"
                "1. DATABASE COLUMNS IN erp_payroll_items:\n"
                "   - `item_category` (VARCHAR): The Japanese expense or allowance category name (e.g. '研修費', '消耗品費', '出張旅費', '交通費精算', '残業手当調整', '接待交際費', '資格取得手当', '扶養控除変更', '役職手当廃止', '未登録手当'). NEVER use 'type' or 'hand_code'!\n"
                "   - `item_type` (VARCHAR): Payment classification. Allowed values: 'Addition' (支給/加算) or 'Deduction' (控除/減算). NEVER use 'type'!\n"
                "   - `raw_amount` (BIGINT): Integer numeric transaction amount in JPY without symbols or commas (e.g. raw_amount > 100000, raw_amount > 150000). ALWAYS use `raw_amount` for amounts; NEVER use 'amount'!\n"
                "   - `employee_name` (VARCHAR): Employee legal name (e.g. '青木 拓也', '菊地 里江', '坂本 裕二').\n"
                "   - `employee_id` (VARCHAR): Employee code (e.g. 'EMP-001', 'EMP-002').\n"
                "   - `id` (VARCHAR): Voucher ID (e.g. 'P4-07089771-001').\n"
                "2. PRECISE SQL MAPPINGS FOR PAYROLL POLICIES:\n"
                "   - Entertainment expense limit (> ¥100,000): sql_condition: \"item_category = '接待交際費' AND raw_amount > 100000\", action_on_match: \"Hold\"\n"
                "   - Deduction item incorrectly registered as Addition: sql_condition: \"item_category IN ('扶養控除変更', '役職手当廃止') AND item_type = 'Addition'\", action_on_match: \"Hold\"\n"
                "   - Single voucher ceiling limit (> ¥150,000): sql_condition: \"raw_amount > 150000\", action_on_match: \"Hold\"\n"
                "   - Unregistered allowance: sql_condition: \"item_category = '未登録手当'\", action_on_match: \"Hold\"\n"
                "   - Pre-approved employee vouchers: sql_condition: \"(id = 'P4-07089771-001' OR employee_name = '青木 拓也') AND item_category = '研修費' AND raw_amount = 77224\", action_on_match: \"Confirmed\"\n"
                "3. REQUIRED JSON FIELDS FOR EVERY RULE:\n"
                "   - \"rule_id\": e.g. \"RULE-PAY-01\"\n"
                "   - \"name\": Concise descriptive rule title\n"
                "   - \"match_field\": Primary column checked (e.g. \"item_category\", \"raw_amount\", \"employee_name\")\n"
                "   - \"match_value\": Target or entity label (TE)\n"
                "   - \"sql_condition\": Valid ANSI SQL predicate against erp_payroll_items\n"
                "   - \"condition\": Same as sql_condition\n"
                "   - \"action_on_match\": \"Hold\" (for holds) or \"Confirmed\" (for approved items)\n"
                "   - \"description\": Professional explanation of the rule\n"
            )
            prompt = f"""Target Process: PAYROLL
Target Database Table: {table_name}
Target Table Schema:
{json.dumps(schema_info, indent=2, ensure_ascii=False)}

Incoming Document / Policy Text:
\"\"\"{policy_text}\"\"\"

Instructions:
1. Extract ALL rules from the document: general principles, approved employee expense lines with rates, hold conditions, amount ceilings, category restrictions, and unregistered allowance checks.
2. For EVERY rule, generate a valid SQL WHERE condition (`sql_condition` and `condition`) that can filter records from `{table_name}`.
3. Every rule MUST include populated non-empty values for: `rule_id`, `name`, `match_field`, `match_value`, `sql_condition`, `condition`, `action_on_match` ("Hold" or "Confirmed"), and `description`.
4. Return ONLY valid JSON with key "item_criteria" without markdown fences."""
        else:
            system_prompt = (
                "You are an Elite Enterprise Database & Policy Rule Extraction Agent specializing in Accounts Payable Invoices (erp_invoices).\n"
                "CRITICAL SCHEMA & DATA TYPE SPECIFICATIONS FOR erp_invoices:\n"
                "1. DATABASE COLUMNS IN erp_invoices:\n"
                "   - Notice: Invoices do NOT have an employee ID! NEVER use 'employee_id' for invoices!\n"
                "   - `vendor_code` (VARCHAR): Vendor ID/Code (e.g. 'V3001'..'V3012'; unregistered: 'V3099'). ALWAYS use `vendor_code` for vendor identification!\n"
                "   - `vendor_name` (VARCHAR): Vendor corporate/business name (e.g. 'Global Tech LLC', '北陸部品工業株式会社').\n"
                "   - `invoice_no` (VARCHAR): Vendor invoice reference number (e.g. 'INV-2026-7353').\n"
                "   - `raw_amount` (BIGINT): Integer numeric transaction amount in JPY without symbols or commas (e.g. raw_amount <= 1500000, raw_amount > 1500000). ALWAYS use `raw_amount` for monetary checks; NEVER use 'amount'!\n"
                "   - `type` (VARCHAR): Invoice classification ('Routine' or 'Adjustment'). NEVER use 'category'!\n"
                "2. PRECISE SQL MAPPINGS FOR INVOICE POLICIES:\n"
                "   - Unregistered vendor check: sql_condition: \"vendor_code NOT IN ('V3001', 'V3002', 'V3004', 'V3005', 'V3006', 'V3007', 'V3008', 'V3009', 'V3010', 'V3011', 'V3012')\", action_on_match: \"Hold\"\n"
                "   - High-value ceiling hold: sql_condition: \"raw_amount > 1500000\", action_on_match: \"Hold\"\n"
                "   - Adjustment review requirement: sql_condition: \"type = 'Adjustment'\", action_on_match: \"Hold\"\n"
                "   - Routine invoice approval: sql_condition: \"type = 'Routine' AND raw_amount <= 1500000 AND vendor_code IN ('V3001', 'V3002', 'V3004', 'V3005', 'V3006', 'V3007', 'V3008', 'V3009', 'V3010', 'V3011', 'V3012')\", action_on_match: \"Approved\"\n"
                "3. REQUIRED JSON FIELDS FOR EVERY RULE:\n"
                "   - \"rule_id\": e.g. \"RULE-INV-01\"\n"
                "   - \"name\": Concise descriptive rule title\n"
                "   - \"match_field\": Primary column checked (e.g. \"vendor_code\", \"raw_amount\", \"type\")\n"
                "   - \"match_value\": Target or entity label (TE)\n"
                "   - \"sql_condition\": Valid ANSI SQL predicate against erp_invoices\n"
                "   - \"condition\": Same as sql_condition\n"
                "   - \"action_on_match\": \"Hold\" or \"Approved\"\n"
                "   - \"description\": Professional explanation\n"
            )
            prompt = f"""Target Process: INVOICE
Target Database Table: {table_name}
Target Table Schema:
{json.dumps(schema_info, indent=2, ensure_ascii=False)}

Incoming Document / Policy Text:
\"\"\"{policy_text}\"\"\"

Instructions:
1. Extract ALL rules from the document: general principles, approved vendor contracts with rates, hold conditions, amount ceilings, category restrictions, vendor-specific exceptions, and unregistered vendor integrity checks.
2. For EVERY rule, generate a valid SQL WHERE condition (`sql_condition` and `condition`) that can filter records from `{table_name}`.
3. Every rule MUST include populated non-empty values for: `rule_id`, `name`, `match_field`, `match_value`, `sql_condition`, `condition`, `action_on_match` ("Hold" or "Approved"), and `description`.
4. Return ONLY valid JSON with key "item_criteria" without markdown fences."""

        rules = []
        try:
            raw_res = self.llm.complete(prompt, system_prompt=system_prompt, timeout=30)
            parsed = clean_and_parse_json_robust(raw_res)
            criteria = parsed.get("item_criteria") or parsed.get("rules") or []
            if isinstance(criteria, list) and criteria:
                rules = criteria
        except Exception as e:
            logging.warning(f"[LLM Extraction Exception] {e}")

        # Fallback semantic parser if LLM output was empty or invalid
        if not rules or not any(r.get("sql_condition") for r in rules):
            rules = self._fallback_semantic_rules(process_type, policy_text)

        # Node 2: Validate and refine SQL rules
        refined_rules = self.validate_and_refine_rules(process_type, rules, policy_text)
        return refined_rules

    # --- Node 2: Validate and Refine Rules ---
    def validate_and_refine_rules(self, process_type: str, rules: List[Dict[str, Any]], policy_text: str) -> List[Dict[str, Any]]:
        """Ensures correct column names, fixes operators, and guarantees case insensitivity."""
        valid_rules = []
        for idx, r in enumerate(rules):
            sql_c = str(r.get("sql_condition") or r.get("condition") or "").strip()
            if not sql_c or "IN ()" in sql_c.upper():
                continue

            # Fix operators
            sql_c = sql_c.replace("==", "=").replace("&&", "AND").replace("||", "OR")

            # Column normalization based on process type
            if process_type in ("leave", "leave_mgmt", "leave_applications"):
                sql_c = re.sub(r'\bdays\b', 'requested_days', sql_c, flags=re.IGNORECASE)
                sql_c = re.sub(r'\bbalance\b', 'remaining_balance', sql_c, flags=re.IGNORECASE)
                sql_c = re.sub(r'\battachment\b', 'has_attachment', sql_c, flags=re.IGNORECASE)
                sql_c = re.sub(r'\btype\b(?=\s*[!=<>]+)', 'leave_type', sql_c, flags=re.IGNORECASE)
                sql_c = re.sub(r'\btype\b(?=\s+(?:IN|NOT\s+IN)\b)', 'leave_type', sql_c, flags=re.IGNORECASE)
                sql_c = re.sub(r'\bhas_attachment\s*=\s*0\b', 'has_attachment = FALSE', sql_c, flags=re.IGNORECASE)
                sql_c = re.sub(r'\bhas_attachment\s*=\s*1\b', 'has_attachment = TRUE', sql_c, flags=re.IGNORECASE)
            elif process_type == "payroll":
                if re.search(r"\btype\s*=\s*'Addition'", sql_c, re.IGNORECASE) or re.search(r"\btype\s*=\s*'Deduction'", sql_c, re.IGNORECASE):
                    sql_c = re.sub(r"\btype\b", "item_type", sql_c, flags=re.IGNORECASE)
                else:
                    sql_c = re.sub(r"\btype\b(?=\s*[!=<>]+\s*['\"])", "item_category", sql_c)
                    sql_c = re.sub(r"\btype\b(?=\s+(?:IN|NOT\s+IN)\b)", "item_category", sql_c, flags=re.IGNORECASE)
                sql_c = re.sub(r"\bamount\b(?=\s*[!=<>]+)", "raw_amount", sql_c, flags=re.IGNORECASE)
                sql_c = re.sub(r"\bhand_code\b", "item_category", sql_c, flags=re.IGNORECASE)
                sql_c = re.sub(r"\bvendor_code\b", "employee_id", sql_c, flags=re.IGNORECASE)
                if r.get("match_field") == "vendor_code":
                    r["match_field"] = "employee_id"
            else:
                # Invoices: ensure vendor_code is used instead of employee_id (Invoices do NOT have employee_id!)
                sql_c = re.sub(r"\bemployee_id\b", "vendor_code", sql_c, flags=re.IGNORECASE)
                sql_c = re.sub(r"\bamount\b(?=\s*[!=<>]+)", "raw_amount", sql_c, flags=re.IGNORECASE)
                if r.get("match_field") == "employee_id":
                    r["match_field"] = "vendor_code"

            r["sql_condition"] = sql_c
            r["condition"] = sql_c

            act = str(r.get("action_on_match") or r.get("action") or "").strip()
            if any(w in act.lower() for w in ["appr", "pass", "ok", "conf", "承"]):
                r["action_on_match"] = "Approved" if process_type == "invoice" else "Confirmed"
            else:
                r["action_on_match"] = "Hold"

            if not r.get("rule_id"):
                r["rule_id"] = f"RULE-{process_type[:3].upper()}-{idx+1:02d}"
            if not r.get("name"):
                r["name"] = r.get("match_value") or f"{process_type.capitalize()} Rule {idx+1}"
            if not r.get("match_value"):
                r["match_value"] = r.get("name") or f"{process_type.capitalize()} Rule {idx+1}"
            if not r.get("description"):
                r["description"] = f"{r.get('action_on_match', 'Hold')} voucher where {sql_c}."

            valid_rules.append(r)

        return valid_rules

    def _fallback_semantic_rules(self, process_type: str, policy_text: str) -> List[Dict[str, Any]]:
        """Fallback deterministic rule generator based on document policy keywords."""
        rules = []
        amts = [int(x.replace(',', '')) for x in re.findall(r'[¥\\]\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,9})', policy_text)]
        if not amts:
            amts = [int(x.replace(',', '')) for x in re.findall(r'([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,9})\s*円', policy_text)]

        all_vendor_codes = sorted(list(set(re.findall(r'\b([A-Z][0-9]{3,5})\b', policy_text))))
        all_vendor_codes = [c for c in all_vendor_codes if not c.startswith('P') and not c.startswith('INV') and c != "UNREGISTERED"]

        if process_type in ("leave", "leave_mgmt", "leave_applications"):
            # 1. Quota Deficit Hold
            rules.append({
                "rule_id": "RULE-LV-01",
                "name": "Leave Quota Deficit Hold",
                "match_field": "requested_days",
                "match_value": "requested_days > remaining_balance",
                "sql_condition": "requested_days > remaining_balance",
                "condition": "requested_days > remaining_balance",
                "action_on_match": "Hold",
                "description": "Leave requests exceeding the remaining paid leave quota must be held for quota adjustment."
            })

            # 2. Consecutive Days Threshold
            days_m = re.search(r'(?:requested_days\s*>\s*([0-9]+(?:\.[0-9]+)?)|([0-9]+)\s*日\s*(?:を超える|超|以上|上限))', policy_text)
            max_days = float(days_m.group(1) or days_m.group(2)) if days_m else 3.0
            rules.append({
                "rule_id": "RULE-LV-02",
                "name": f"Long Consecutive Leave Approval ({int(max_days)} Days Limit)",
                "match_field": "requested_days",
                "match_value": f"requested_days > {max_days}",
                "sql_condition": f"requested_days > {max_days}",
                "condition": f"requested_days > {max_days}",
                "action_on_match": "Hold",
                "description": f"Consecutive leave requests exceeding {int(max_days)} days require department director approval."
            })

            # 3. Medical Leave Without Doctor's Certificate
            rules.append({
                "rule_id": "RULE-LV-03",
                "name": "Sick Leave Certificate Required",
                "match_field": "has_attachment",
                "match_value": "Sick Leave Missing Attachment",
                "sql_condition": "leave_type = '病気休暇' AND has_attachment = FALSE",
                "condition": "leave_type = '病気休暇' AND has_attachment = FALSE",
                "action_on_match": "Hold",
                "description": "Medical/sick leave applications without an attached medical certificate (医師診断書) are held."
            })

            # 4. Bereavement Leave Documentation Required
            rules.append({
                "rule_id": "RULE-LV-04",
                "name": "Bereavement Leave Documentation Required",
                "match_field": "has_attachment",
                "match_value": "Bereavement Missing Attachment",
                "sql_condition": "leave_type = '慶弔特別休暇' AND has_attachment = FALSE",
                "condition": "leave_type = '慶弔特別休暇' AND has_attachment = FALSE",
                "action_on_match": "Hold",
                "description": "Special bereavement leave without supporting documentation is placed on hold."
            })

            # 5. Departmental Specific Freeze / Audit Rules
            dept_m = re.search(r'department\s*(?:IN\s*\([^)]+\)|=\s*\'[^\']+\')(?:\s*AND\s*requested_days\s*>\s*[0-9]+(?:\.[0-9]+)?)?', policy_text, re.IGNORECASE)
            if dept_m:
                dept_cond = dept_m.group(0)
                rules.append({
                    "rule_id": "RULE-LV-DEPT",
                    "name": "Departmental Project Freeze Audit",
                    "match_field": "department",
                    "match_value": dept_cond,
                    "sql_condition": dept_cond,
                    "condition": dept_cond,
                    "action_on_match": "Hold",
                    "description": f"Leave requests under departmental freeze ({dept_cond}) require departmental interview."
                })

            # 6. Unregistered Leave Type Integrity Check
            rules.append({
                "rule_id": "RULE-LV-05",
                "name": "Unregistered Leave Type Integrity Check",
                "match_field": "leave_type",
                "match_value": "未登録休暇",
                "sql_condition": "leave_type = '未登録休暇'",
                "condition": "leave_type = '未登録休暇'",
                "action_on_match": "Hold",
                "description": "Unregistered or undefined leave types must be reviewed by HR administration."
            })

            # 7. Standard Approved Leave Categories
            rules.append({
                "rule_id": "RULE-LV-06",
                "name": "Approved Standard Paid Leave",
                "match_field": "leave_type",
                "match_value": "Standard Compliant Leave",
                "sql_condition": f"leave_type IN ('有給休暇', '半日有給申請', '夏季特別休暇', '在宅研修休暇') AND requested_days <= remaining_balance AND requested_days <= {max_days}",
                "condition": f"leave_type IN ('有給休暇', '半日有給申請', '夏季特別休暇', '在宅研修休暇') AND requested_days <= remaining_balance AND requested_days <= {max_days}",
                "action_on_match": "Approved",
                "description": f"Standard leave requests within quota and under {int(max_days)} days are automatically approved."
            })
            return rules

        elif process_type == "payroll":
            # Dynamic single voucher ceiling
            ceil_m = re.search(r'(?:単一|1件あたり|上限|ceiling|limit|maximum)[^\n\r0-9]*?[¥\\]?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,9})', policy_text, re.IGNORECASE)
            p_limit = int(ceil_m.group(1).replace(',', '')) if ceil_m else 150000

            # Dynamic entertainment limit
            if re.search(r'接待交際費[^\n\r]*?全件保留', policy_text):
                rules.append({
                    "rule_id": "RULE-PAY-01",
                    "name": "Entertainment Full Hold",
                    "match_field": "item_category",
                    "match_value": "接待交際費 (全件保留)",
                    "sql_condition": "item_category = '接待交際費'",
                    "condition": "item_category = '接待交際費'",
                    "action_on_match": "Hold",
                    "description": "All entertainment expenses are placed on hold per policy."
                })
            else:
                ent_m = re.search(r'接待交際費[^\n\r0-9]*?[¥\\]?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,9})', policy_text)
                ent_limit = int(ent_m.group(1).replace(',', '')) if ent_m else 100000
                rules.append({
                    "rule_id": "RULE-PAY-01",
                    "name": "Entertainment Expense Ceiling",
                    "match_field": "raw_amount",
                    "match_value": f"接待交際費 (> ¥{ent_limit:,})",
                    "sql_condition": f"item_category = '接待交際費' AND raw_amount > {ent_limit}",
                    "condition": f"item_category = '接待交際費' AND raw_amount > {ent_limit}",
                    "action_on_match": "Hold",
                    "description": f"Entertainment expenses exceeding ¥{ent_limit:,} must be held for executive approval."
                })

            # Deduction Classification Mismatch
            rules.append({
                "rule_id": "RULE-PAY-02",
                "name": "Deduction Classification Mismatch",
                "match_field": "item_category",
                "match_value": "Deduction Items as Addition",
                "sql_condition": "item_category IN ('扶養控除変更', '役職手当廃止') AND item_type = 'Addition'",
                "condition": "item_category IN ('扶養控除変更', '役職手当廃止') AND item_type = 'Addition'",
                "action_on_match": "Hold",
                "description": "Deduction items incorrectly marked as Addition held for payroll review."
            })

            # Specific Category Hold Rules
            cons_m = re.search(r'消耗品費[^\n\r0-9]*?[¥\\]?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,9})', policy_text)
            if cons_m and "保留" in policy_text:
                c_limit = int(cons_m.group(1).replace(',', ''))
                rules.append({
                    "rule_id": "RULE-PAY-CONS",
                    "name": "Consumables Procurement Threshold",
                    "match_field": "raw_amount",
                    "match_value": f"消耗品費 (> ¥{c_limit:,})",
                    "sql_condition": f"item_category = '消耗品費' AND raw_amount > {c_limit}",
                    "condition": f"item_category = '消耗品費' AND raw_amount > {c_limit}",
                    "action_on_match": "Hold",
                    "description": f"Consumables exceeding ¥{c_limit:,} held for asset review."
                })

            ot_m = re.search(r'残業手当調整[^\n\r0-9]*?[¥\\]?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,9})', policy_text)
            if ot_m and "保留" in policy_text:
                ot_limit = int(ot_m.group(1).replace(',', ''))
                rules.append({
                    "rule_id": "RULE-PAY-OT",
                    "name": "Overtime Adjustment Audit",
                    "match_field": "raw_amount",
                    "match_value": f"残業手当調整 (> ¥{ot_limit:,})",
                    "sql_condition": f"item_category = '残業手当調整' AND raw_amount > {ot_limit}",
                    "condition": f"item_category = '残業手当調整' AND raw_amount > {ot_limit}",
                    "action_on_match": "Hold",
                    "description": f"Overtime adjustments exceeding ¥{ot_limit:,} held for attendance check."
                })

            if re.search(r'役職手当新設[^\n\r]*?保留', policy_text):
                rules.append({
                    "rule_id": "RULE-PAY-POS",
                    "name": "Leadership Allowance Review",
                    "match_field": "item_category",
                    "match_value": "役職手当新設 (保留)",
                    "sql_condition": "item_category = '役職手当新設'",
                    "condition": "item_category = '役職手当新設'",
                    "action_on_match": "Hold",
                    "description": "Leadership allowance updates held for committee verification."
                })

            # Single Voucher Ceiling
            rules.append({
                "rule_id": "RULE-PAY-03",
                "name": "Single Voucher Ceiling",
                "match_field": "raw_amount",
                "match_value": f"Ceiling Limit (> ¥{p_limit:,})",
                "sql_condition": f"raw_amount > {p_limit}",
                "condition": f"raw_amount > {p_limit}",
                "action_on_match": "Hold",
                "description": f"Single voucher amounts exceeding ¥{p_limit:,} held for secondary review."
            })

            # Unregistered Allowance Check
            rules.append({
                "rule_id": "RULE-PAY-UNK",
                "name": "Unregistered Allowance Code Check",
                "match_field": "item_category",
                "match_value": "未登録手当",
                "sql_condition": "item_category = '未登録手当'",
                "condition": "item_category = '未登録手当'",
                "action_on_match": "Hold",
                "description": "Unregistered allowance codes are placed on hold for HR inspection."
            })

            # Dynamic Approved Categories
            valid_cats = ['研修費', '消耗品費', '出張旅費', '交通費精算', '残業手当調整', '資格取得手当', '在宅勤務手当']
            mentioned_cats = [c for c in valid_cats if c in policy_text]
            approved_cats = mentioned_cats if mentioned_cats else ['研修費', '消耗品費', '出張旅費', '交通費精算', '残業手当調整', '資格取得手当']
            cats_str = ", ".join([f"'{c}'" for c in approved_cats])

            rules.append({
                "rule_id": "RULE-PAY-04",
                "name": "Approved Standard Allowances",
                "match_field": "item_category",
                "match_value": "Approved Categories",
                "sql_condition": f"item_category IN ({cats_str}) AND raw_amount <= {p_limit}",
                "condition": f"item_category IN ({cats_str}) AND raw_amount <= {p_limit}",
                "action_on_match": "Confirmed",
                "description": f"Routine expense reimbursements compliant with limits confirmed."
            })
        else:
            unregistered_codes = set(re.findall(r'(?:未登録|unregistered)[^\n\r]*?\b([A-Z][0-9]{3,5})\b', policy_text, re.IGNORECASE))
            unregistered_codes.add("V3099")
            reg_vendor_codes = [c for c in all_vendor_codes if c not in unregistered_codes]

            # Specific Vendor Hold Rules (e.g. V3005 is held, V3006 is held)
            vendor_hold_matches = re.findall(r'\b(V300[0-9]|V301[0-2])\b[^\n\r]*?(?:保留|hold|交渉中|更新中)', policy_text, re.IGNORECASE)
            v_hold_set = sorted(list(set(vendor_hold_matches))) if vendor_hold_matches else []
            if v_hold_set:
                v_hold_str = ", ".join([f"'{v}'" for v in v_hold_set])
                rules.append({
                    "rule_id": "RULE-INV-VHOLD",
                    "name": f"Specific Vendor Audit Hold",
                    "match_field": "vendor_code",
                    "match_value": f"Audited Vendors ({', '.join(v_hold_set)})",
                    "sql_condition": f"vendor_code IN ({v_hold_str})",
                    "condition": f"vendor_code IN ({v_hold_str})",
                    "action_on_match": "Hold",
                    "description": f"Invoices from {', '.join(v_hold_set)} require manual review per policy."
                })
                reg_vendor_codes = [c for c in reg_vendor_codes if c not in v_hold_set]

            # Check ceiling
            ceiling_match = re.search(r'(?:限度額|超過|上限|ceiling|limit|exceeding|not\s+exceed)[^\n\r0-9]*?[¥\\]?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,9})', policy_text, re.IGNORECASE)
            has_explicit_ceiling = bool(ceiling_match)
            if ceiling_match:
                limit = int(ceiling_match.group(1).replace(',', ''))
            else:
                limit = 2000000

            # Standard Registered Vendors list
            standard_registered = ['V3001', 'V3002', 'V3004', 'V3005', 'V3006', 'V3007', 'V3008', 'V3009', 'V3010', 'V3011', 'V3012']
            active_registered = reg_vendor_codes if len(reg_vendor_codes) >= 4 else standard_registered
            codes_str = ", ".join([f"'{c}'" for c in active_registered])

            rules.append({
                "rule_id": "RULE-INV-01",
                "name": "Unregistered Vendor Integrity Check",
                "match_field": "vendor_code",
                "match_value": "Unregistered Vendors",
                "sql_condition": f"vendor_code NOT IN ({codes_str})",
                "condition": f"vendor_code NOT IN ({codes_str})",
                "action_on_match": "Hold",
                "description": "Invoices from vendors not registered in the approved database must be placed on hold."
            })

            # High-value ceiling hold (only if explicitly requested or general policy)
            if has_explicit_ceiling:
                rules.append({
                    "rule_id": "RULE-INV-02",
                    "name": "High-Value Policy Ceiling",
                    "match_field": "raw_amount",
                    "match_value": f"Ceiling (> ¥{limit:,})",
                    "sql_condition": f"raw_amount > {limit}",
                    "condition": f"raw_amount > {limit}",
                    "action_on_match": "Hold",
                    "description": f"Invoices exceeding ¥{limit:,} require secondary authorization."
                })

            # Adjustment category review
            rules.append({
                "rule_id": "RULE-INV-03",
                "name": "Adjustment Review Requirement",
                "match_field": "type",
                "match_value": "Adjustment Category",
                "sql_condition": "type = 'Adjustment'",
                "condition": "type = 'Adjustment'",
                "action_on_match": "Hold",
                "description": "All adjustment category items require manual accounting verification."
            })

            # Individual Vendor Contract Rules (extract contract lines like Global Tech LLC ¥716,232)
            items = re.split(r'\n(?=[0-9]+[\.\:]\s*)', policy_text)
            v_idx = 1
            for itm in items:
                v_code_m = re.search(r'\b(V300[0-9]|V301[0-2])\b', itm)
                if not v_code_m:
                    continue
                v_code = v_code_m.group(1)
                if v_code in v_hold_set:
                    continue
                v_name_m = re.search(r'([A-Za-z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\s\.\,\-]+?)\s*[\(（]', itm)
                v_name = v_name_m.group(1).strip() if v_name_m else v_code
                v_name = re.sub(r'^[0-9]+[\.\:]\s*', '', v_name).strip()
                v_amts = [int(x.replace(',', '')) for x in re.findall(r'[¥\\]\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,9})', itm)]
                if not v_amts:
                    v_amts = [int(x.replace(',', '')) for x in re.findall(r'([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,9})\s*円', itm)]

                if v_amts:
                    if len(v_amts) == 1:
                        cond = f"vendor_code = '{v_code}' AND raw_amount = {v_amts[0]}"
                    else:
                        cond = f"vendor_code = '{v_code}' AND raw_amount IN ({', '.join(map(str, v_amts))})"
                    rules.append({
                        "rule_id": f"RULE-INV-V{v_idx:02d}",
                        "name": f"{v_name} Contract Rate Approval",
                        "match_field": "vendor_code",
                        "match_value": f"{v_name} ({v_code})",
                        "sql_condition": cond,
                        "condition": cond,
                        "action_on_match": "Approved",
                        "description": f"Pre-approved recurring contract terms for {v_name} ({v_code}) confirmed compliant."
                    })
                    v_idx += 1
                else:
                    cond = f"vendor_code = '{v_code}' AND type = 'Routine'"
                    rules.append({
                        "rule_id": f"RULE-INV-V{v_idx:02d}",
                        "name": f"{v_name} Routine Approval",
                        "match_field": "vendor_code",
                        "match_value": f"{v_name} ({v_code})",
                        "sql_condition": cond,
                        "condition": cond,
                        "action_on_match": "Approved",
                        "description": f"Routine transactions for {v_name} ({v_code}) approved within policy terms."
                    })
                    v_idx += 1

            # General Routine Approval
            rules.append({
                "rule_id": "RULE-INV-ROUTINE",
                "name": "General Routine Invoice Approval",
                "match_field": "type",
                "match_value": "Routine Invoices",
                "sql_condition": f"type = 'Routine' AND raw_amount <= {limit} AND vendor_code IN ({codes_str})",
                "condition": f"type = 'Routine' AND raw_amount <= {limit} AND vendor_code IN ({codes_str})",
                "action_on_match": "Approved",
                "description": f"Routine invoices under ¥{limit:,} from registered vendors are automatically approved."
            })

        return rules

    # --- Node 3: Evaluate Rows & Generate Decisions ---
    def evaluate_rows(self, process_type: str, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluates database rows against extracted SQL rules with Hold precedence and generates certified comments."""
        t0 = time.time()
        if process_type in ("leave", "leave_mgmt", "leave_applications"):
            table_name = "erp_leave_applications"
        elif process_type == "payroll":
            table_name = "erp_payroll_items"
        else:
            table_name = "erp_invoices"
        conn = None
        try:
            conn = self.get_connection()
        except Exception as conn_err:
            logging.warning(f"[Live DB Connection Error in evaluate_rows] {conn_err}")

        try:
            db_rows = self.fetch_all_rows(table_name, conn=conn)

            hold_rules = [r for r in rules if r.get("action_on_match") in ("Hold", "Rejected")]
            appr_rules = [r for r in rules if r.get("action_on_match") in ("Approved", "Confirmed")]

            # Query live DB sets for each rule for 100% precision using shared single connection
            hold_matches_by_rule = {}
            appr_matches_by_rule = {}

            for hr in hold_rules:
                cond = hr.get("sql_condition") or hr.get("condition") or ""
                r_key = hr.get("rule_id", id(hr))
                if cond:
                    db_set = self.query_matching_ids(table_name, cond, conn=conn)
                    hold_matches_by_rule[r_key] = db_set

            for ar in appr_rules:
                cond = ar.get("sql_condition") or ar.get("condition") or ""
                r_key = ar.get("rule_id", id(ar))
                if cond:
                    db_set = self.query_matching_ids(table_name, cond, conn=conn)
                    appr_matches_by_rule[r_key] = db_set
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

        decisions = []
        discrepancies = []

        for row in db_rows:
            row_id = str(row.get("id"))
            amount = row.get("raw_amount", 0)

            # Hold checks (Hold rules ALWAYS take precedence!)
            matched_hold_rules = []
            reasons = []

            for hr in hold_rules:
                r_key = hr.get("rule_id", id(hr))
                cond = hr.get("sql_condition") or hr.get("condition") or ""
                db_set = hold_matches_by_rule.get(r_key)
                if db_set is not None:
                    matched = (row_id in db_set)
                else:
                    matched = evaluate_sql_condition_in_memory(row, cond)

                if matched:
                    matched_hold_rules.append(hr)
                    rule_label = hr.get("name") or hr.get("match_value", "Hold Rule")
                    rule_desc = hr.get("description", "")
                    reasons.append(f"{rule_label}: Matched SQL condition ({cond}). {rule_desc}")

            if matched_hold_rules:
                new_status = "Hold"
                matched_rule_id = ", ".join([hr.get("rule_id", "RULE-HOLD") for hr in matched_hold_rules if hr.get("rule_id")])
                matched_rule_summary = "; ".join([hr.get("name") or hr.get("match_value", "Hold Policy Rule") for hr in matched_hold_rules])
            else:
                # Approval checks
                matched_appr_rule = None
                for ar in appr_rules:
                    r_key = ar.get("rule_id", id(ar))
                    cond = ar.get("sql_condition") or ar.get("condition") or ""
                    db_set = appr_matches_by_rule.get(r_key)
                    if db_set is not None:
                        matched = (row_id in db_set)
                    else:
                        matched = evaluate_sql_condition_in_memory(row, cond)

                    if matched:
                        matched_appr_rule = ar
                        rule_label = ar.get("name") or ar.get("match_value", "Approval Rule")
                        rule_desc = ar.get("description", "")
                        reasons.append(f"{rule_label}: Complies with SQL condition ({cond}). {rule_desc}")
                        break

                if matched_appr_rule:
                    new_status = "Approved" if process_type == "invoice" else "Confirmed"
                    matched_rule_id = matched_appr_rule.get("rule_id", "RULE-APPROVED")
                    matched_rule_summary = matched_appr_rule.get("name") or matched_appr_rule.get("match_value", "Approved Contract Rule")
                else:
                    new_status = "Hold"
                    matched_rule_id = "RULE-UNMATCHED"
                    matched_rule_summary = "Unmatched Policy Criteria"
                    reasons.append("Voucher does not satisfy any approved routine contract SQL criteria (requires manual review).")

            # Certified Japanese audit comment
            formatted_amt = f"¥{amount:,}"
            if reasons:
                main_reason = reasons[0]
                if new_status in ("Approved", "Confirmed"):
                    comment = f"【自動承認】{main_reason}"
                else:
                    comment = f"【保留】{main_reason}"
            else:
                if new_status in ("Approved", "Confirmed"):
                    comment = f"【自動承認】規程適合確認済（金額: {formatted_amt}）"
                else:
                    comment = f"【保留】手動精査が必要（金額: {formatted_amt}）"

            entity_name = row.get("name") or row.get("employee_name", "")
            ref_val = row.get("invoice_no") or row.get("voucher_ref", "")
            is_leave = (table_name == "erp_leave_applications")
            
            if is_leave:
                req_days = float(row.get("requested_days", 0) or 0)
                rem_bal = float(row.get("remaining_balance", 0) or 0)
                formatted_amt = f"{req_days:.1f}日 (残: {rem_bal:.1f}日)"
                if reasons:
                    comment = f"【自動承認】{reasons[0]}" if new_status in ("Approved", "Confirmed") else f"【保留】{reasons[0]}"
                else:
                    comment = f"【自動承認】申請内容規程適合（{formatted_amt}）" if new_status in ("Approved", "Confirmed") else f"【保留】要人事確認（{formatted_amt}）"

            rec = {
                "id": row.get("id"),
                "employee_id": row.get("employee_id"),
                "name": entity_name,
                "employee_name": entity_name,
                "entity_name": entity_name,
                "item_category": row.get("leave_type") or row.get("item_category") or row.get("type", ""),
                "type": row.get("leave_type") or row.get("type") or row.get("item_type", ""),
                "department": row.get("department", ""),
                "leave_type": row.get("leave_type", ""),
                "requested_days": float(row.get("requested_days", 0) or 0) if is_leave else 0,
                "remaining_balance": float(row.get("remaining_balance", 0) or 0) if is_leave else 0,
                "start_date": row.get("start_date", ""),
                "end_date": row.get("end_date", ""),
                "reason": row.get("reason", ""),
                "has_attachment": bool(row.get("has_attachment", False)),
                "attachment_name": row.get("attachment_name") or "",
                "ref": ref_val,
                "raw_amount": amount if not is_leave else float(row.get("requested_days", 0) or 0),
                "amount": formatted_amt,
                "current_status": row.get("status", "Unprocessed"),
                "new_status": new_status,
                "matched_rule_id": matched_rule_id,
                "matched_rule": matched_rule_summary,
                "matched_rule_summary": matched_rule_summary,
                "reasons": reasons,
                "comment": comment
            }
            decisions.append(rec)
            if new_status == "Hold":
                discrepancies.append(rec)

        approved_count = sum(1 for d in decisions if d["new_status"] in ("Approved", "Confirmed"))
        hold_count = len(discrepancies)

        return {
            "status": "STAGED",
            "process_type": process_type,
            "table_name": table_name,
            "duration_s": round(time.time() - t0, 3),
            "total_evaluated": len(decisions),
            "approved_count": approved_count,
            "hold_count": hold_count,
            "rules": rules,
            "decisions": decisions,
            "discrepancies": discrepancies,
            "summary": f"Evaluated {len(decisions)} rows: {approved_count} Approved, {hold_count} On Hold (Staged for user commit)."
        }

    # --- Node 4: Commit Updates to Database (Modifies ONLY target column & comments) ---
    def commit_database_updates(self, process_type: str, decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Atomically updates ONLY the target column ('status') and 'comment' column in PostgreSQL."""
        t0 = time.time()
        if process_type in ("leave", "leave_mgmt", "leave_applications"):
            table_name = "erp_leave_applications"
        elif process_type == "payroll":
            table_name = "erp_payroll_items"
        else:
            table_name = "erp_invoices" 

        if not decisions:
            return {"status": "SKIPPED", "updated_count": 0, "message": "No decisions to commit."}

        params = [(d["new_status"], d["comment"], d["id"]) for d in decisions]

        with self.get_connection() as conn:
            is_pg = hasattr(conn, "cursor_factory") or "psycopg" in str(type(conn)).lower()
            ph = "%s" if is_pg else "?"
            update_query = f"""
                UPDATE {table_name}
                SET status = {ph},
                    comment = {ph}
                WHERE id = {ph};
            """
            cur = conn.cursor()
            cur.executemany(update_query, params)
            conn.commit()

        lat = round(time.time() - t0, 3)
        return {
            "status": "COMMITTED",
            "table_name": table_name,
            "updated_count": len(decisions),
            "duration_s": lat,
            "message": f"Successfully updated target column 'status' and 'comment' for {len(decisions)} records in {table_name} in {lat}s."
        }
