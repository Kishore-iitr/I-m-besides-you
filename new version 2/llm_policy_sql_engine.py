"""
LLM Policy to SQL Engine & Human Intervention Orchestrator (Zero-Hardcoding Edition)
Extracts business rules dynamically from ANY uploaded policy document (.docx/.txt) using an LLM,
compiles them into a valid JSON containing executable PostgreSQL SELECT queries,
executes them against the live PostgreSQL `erp_invoices` table, flags discrepancies for human intervention,
and provides single-use dispatch tokens to prevent repeat ERP auto-run on page refresh.
"""

import os
import re
import sys
import json
import time
import uuid
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional
from erp_db import db_manager
from tmi_pipeline import PuterLlmClient

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

GENERATED_JSON_PATH = Path(__file__).parent / "active_policy_queries.json"
DECISION_CACHE_PATH = Path(__file__).parent / "active_decisions_state.json"
DISPATCH_TOKENS_FILE = Path(__file__).parent / "active_dispatch_tokens.json"

def _load_tokens() -> Dict[str, Any]:
    if DISPATCH_TOKENS_FILE.exists():
        try:
            with open(DISPATCH_TOKENS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_tokens(tokens: Dict[str, Any]):
    with open(DISPATCH_TOKENS_FILE, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2)

class LlmPolicySqlEngine:
    """Zero-hardcoding engine: Pure LLM document analysis, PostgreSQL query synthesis & human review."""

    def __init__(self):
        os.environ["PUTER_MODEL"] = "gpt-4o-mini"
        self.llm = PuterLlmClient(model="gpt-4o-mini")

    def generate_sql_policy_from_doc(self, doc_text: str, filename_or_title: str = "Uploaded Policy Document") -> Dict[str, Any]:
        """
        Dynamically analyzes ANY policy document using the LLM.
        Inspects the live database context and converts the text into valid PostgreSQL queries in JSON format.
        No hardcoded vendors, thresholds, or queries.
        """
        # Fetch current invoice records from PostgreSQL to ground the LLM with live schema context
        try:
            current_rows = db_manager.fetch_all()
            db_sample = [
                {
                    "name": inv["name"],
                    "raw_amount": inv["raw_amount"],
                    "type": inv["type"],
                    "invoice_no": inv["invoice_no"]
                }
                for inv in current_rows
            ]
        except Exception:
            db_sample = []

        system_prompt = (
            "You are an expert PostgreSQL Database Architect and Senior Enterprise Financial Auditor. "
            "Your task is to analyze ANY corporate policy document provided by the user, extract the underlying "
            "business and audit rules, and synthesize valid, executable PostgreSQL SELECT queries to evaluate invoice records in the table `erp_invoices`."
        )

        user_prompt = f"""
Analyze the following policy document and dynamically synthesize executable PostgreSQL SELECT queries to evaluate the invoices in the database.

Target PostgreSQL Table: `erp_invoices`
Schema Columns:
- `id` (VARCHAR): Unique invoice ID (Primary Key)
- `employee_id` (VARCHAR): Vendor ID code (e.g. 'V3005')
- `name` (VARCHAR): Vendor name (e.g. 'Global Tech LLC')
- `invoice_no` (VARCHAR): Invoice identifier (e.g. 'INV-2026-7344')
- `amount` (VARCHAR): Display amount string (e.g. '¥716,232')
- `raw_amount` (INTEGER/NUMERIC): Actual invoiced numeric amount in JPY (e.g. 716232)
- `type` (VARCHAR): Category (e.g. 'Routine' or 'Adjustment')
- `status` (VARCHAR): Invoice status ('Unprocessed', 'Approved', 'On Hold')
- `ref` (VARCHAR): Order reference string

Sample of existing invoice records in the database:
{json.dumps(db_sample, indent=2, ensure_ascii=False)}

Document Source / Title: {filename_or_title}
Raw Policy Document Text:
\"\"\"
{doc_text}
\"\"\"

Requirements:
1. Synthesize the business logic purely from the document text.
2. In 'rules', produce an array of rule objects where each rule contains:
   - `rule_id`: Identifier (e.g. "rule_1")
   - `rule_name`: Short descriptive name of the rule
   - `target_action`: Exactly "approve" or "hold"
   - `comment`: Professional audit verification note explaining the basis for approval or hold
   - `sql_query`: A valid PostgreSQL query starting with `SELECT id FROM erp_invoices WHERE ...`
3. In 'discrepancy_query', provide a SQL query (`SELECT id FROM erp_invoices WHERE ...`) that identifies invoice rows that represent discrepancies, rate variances, unlisted vendors, or unfulfilled inspection criteria requiring human review.
4. In 'discrepancy_reason', describe what constitutes a discrepancy under this policy.
5. Return ONLY a valid JSON object matching the exact structure below.

Expected JSON Structure:
{{
  "policy_title": "Extracted document title",
  "summary": "1-2 sentence executive summary of the extracted rules",
  "rules": [
    {{
      "rule_id": "rule_1",
      "rule_name": "Rule description",
      "target_action": "approve",
      "comment": "Audit verification note",
      "sql_query": "SELECT id FROM erp_invoices WHERE ..."
    }}
  ],
  "discrepancy_query": "SELECT id FROM erp_invoices WHERE ...",
  "discrepancy_reason": "Reason why human intervention is needed"
}}
"""

        # Call LLM with exponential backoff retry in case of transient 429 rate limit
        last_error = None
        for attempt in range(4):
            try:
                result = self.llm.complete_json(user_prompt, system_prompt=system_prompt, timeout=60)
                if result and isinstance(result, dict) and "rules" in result and result.get("rules"):
                    # Sanitize and balance all queries
                    for r in result.get("rules", []):
                        r["sql_query"] = self._clean_sql(r.get("sql_query", ""))
                    if "discrepancy_query" in result:
                        result["discrepancy_query"] = self._clean_sql(result.get("discrepancy_query", ""))
                    
                    # Persist the valid JSON file
                    with open(GENERATED_JSON_PATH, "w", encoding="utf-8") as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)
                    
                    return result
            except Exception as e:
                last_error = e
                time.sleep(1.5 * (attempt + 1))
        
        # If repeated LLM failure, raise clear exception rather than using hardcoded fallbacks!
        raise RuntimeError(f"LLM compilation failed after multiple attempts: {last_error}")

    def execute_sql_rules_against_pg(self, policy_json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes the generated SQL queries against PostgreSQL `erp_invoices` table.
        Flags discrepancies for Human Intervention.
        """
        if not policy_json:
            if GENERATED_JSON_PATH.exists():
                with open(GENERATED_JSON_PATH, "r", encoding="utf-8") as f:
                    policy_json = json.load(f)
            else:
                raise RuntimeError("No active policy queries found. Please upload or compile a document first.")

        # Fetch all invoice rows from PostgreSQL
        all_invoices = db_manager.fetch_all()
        invoice_map = {inv["id"]: inv for inv in all_invoices}

        # Track results per invoice
        evaluated: Dict[str, Dict[str, Any]] = {}
        for inv_id, inv in invoice_map.items():
            evaluated[inv_id] = {
                "id": inv_id,
                "invoice_no": inv["invoice_no"],
                "name": inv["name"],
                "amount": inv["amount"],
                "raw_amount": inv["raw_amount"],
                "type": inv["type"],
                "status": inv["status"],
                "decision": "On Hold",
                "action": "hold",
                "comment": "On hold for audit verification.",
                "matched_rules": [],
                "is_discrepancy": False,
                "discrepancy_detail": None,
                "human_override": False
            }

        # Execute each rule query synthesized by the LLM
        rules = policy_json.get("rules", [])
        for rule in rules:
            query = rule.get("sql_query", "").strip()
            action = rule.get("target_action", "hold").lower()
            comment = rule.get("comment", "")
            rule_name = rule.get("rule_name", rule.get("rule_id", "rule"))

            matched_ids = self._run_query_ids(query)
            for m_id in matched_ids:
                if m_id in evaluated:
                    item = evaluated[m_id]
                    item["matched_rules"].append(rule_name)
                    if action == "approve":
                        item["decision"] = "Approved"
                        item["action"] = "approve"
                        item["comment"] = comment
                    else:
                        if item["decision"] != "Approved":
                            item["decision"] = "On Hold"
                            item["action"] = "hold"
                            item["comment"] = comment

        # Run discrepancy query synthesized by the LLM
        disc_query = policy_json.get("discrepancy_query", "").strip()
        disc_reason = policy_json.get("discrepancy_reason", "Policy variance requiring human audit review.")
        if disc_query:
            disc_ids = self._run_query_ids(disc_query)
            for d_id in disc_ids:
                if d_id in evaluated:
                    evaluated[d_id]["is_discrepancy"] = True
                    evaluated[d_id]["discrepancy_detail"] = disc_reason

        # Invoices with zero matched rules are also flagged for human review
        for inv_id, item in evaluated.items():
            if len(item["matched_rules"]) == 0:
                item["is_discrepancy"] = True
                item["discrepancy_detail"] = "Invoice does not match any LLM-synthesized SQL rule."

        # Separate into summary categories
        approved_items = [v for v in evaluated.values() if v["decision"] == "Approved" and not v["is_discrepancy"]]
        held_items = [v for v in evaluated.values() if v["decision"] == "On Hold" and not v["is_discrepancy"]]
        discrepancies = [v for v in evaluated.values() if v["is_discrepancy"]]

        summary_report = {
            "policy_id": policy_json.get("policy_id", "llm_policy"),
            "policy_title": policy_json.get("policy_title", "Compiled Invoice Policy"),
            "summary": policy_json.get("summary", ""),
            "generated_sql_rules": rules,
            "total_invoices": len(all_invoices),
            "approved_count": len(approved_items),
            "held_count": len(held_items),
            "discrepancy_count": len(discrepancies),
            "discrepancies": discrepancies,
            "evaluated_invoices": evaluated,
            "db_status": db_manager.get_status()
        }

        # Save active decision state for ERP consumption
        with open(DECISION_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(summary_report, f, indent=2, ensure_ascii=False)

        return summary_report

    def _clean_sql(self, query: str) -> str:
        """Sanitizes query and ensures balanced parentheses and semicolon."""
        q = query.strip()
        if not q.upper().startswith("SELECT"):
            q = f"SELECT id FROM erp_invoices WHERE {q}"
        if q.endswith(";"):
            q = q[:-1].strip()
        open_c = q.count("(")
        close_c = q.count(")")
        if open_c > close_c:
            q += ")" * (open_c - close_c)
        return q + ";"

    def _run_query_ids(self, query: str) -> List[str]:
        """Executes a SQL query against the database and returns matching invoice IDs."""
        if not query or not query.strip().upper().startswith("SELECT"):
            return []
        
        q = self._clean_sql(query)

        try:
            if db_manager.engine_type == "postgresql":
                import psycopg2.extras
                with db_manager._get_pg_conn() as conn:
                    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                        cur.execute(q)
                        rows = cur.fetchall()
                        return [str(r.get("id")) for r in rows if r.get("id")]
            else:
                with db_manager._get_sqlite_conn() as conn:
                    conn.row_factory = sqlite3.Row
                    cur = conn.cursor()
                    cur.execute(q)
                    rows = cur.fetchall()
                    return [str(dict(r).get("id")) for r in rows if dict(r).get("id")]
        except Exception as e:
            print(f"[LlmPolicySqlEngine] Query error on '{q}': {e}", file=sys.stderr)
            return []

    def apply_human_override(self, invoice_id: str, action: str, comment: str) -> Dict[str, Any]:
        """Applies human reviewer's override decision to a specific invoice discrepancy."""
        if DECISION_CACHE_PATH.exists():
            with open(DECISION_CACHE_PATH, "r", encoding="utf-8") as f:
                state = json.load(f)
        else:
            state = self.execute_sql_rules_against_pg()

        ev = state.get("evaluated_invoices", {})
        if invoice_id in ev:
            ev[invoice_id]["decision"] = "Approved" if action.lower() in ["approve", "approved"] else "On Hold"
            ev[invoice_id]["action"] = action.lower()
            ev[invoice_id]["comment"] = comment
            ev[invoice_id]["is_discrepancy"] = False
            ev[invoice_id]["human_override"] = True

            state["approved_count"] = sum(1 for v in ev.values() if v["decision"] == "Approved" and not v.get("is_discrepancy"))
            state["held_count"] = sum(1 for v in ev.values() if v["decision"] == "On Hold" and not v.get("is_discrepancy"))
            state["discrepancy_count"] = sum(1 for v in ev.values() if v.get("is_discrepancy"))
            state["discrepancies"] = [v for v in ev.values() if v.get("is_discrepancy")]

            with open(DECISION_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)

        return state

    def create_dispatch_token(self, policy_id: str) -> str:
        """
        Creates a one-time execution token for the ERP tab automation.
        Prevents page refresh in ERP from restarting automation repeatedly!
        """
        token = uuid.uuid4().hex
        tokens = _load_tokens()
        tokens[token] = {
            "token": token,
            "policy_id": policy_id,
            "created_at": time.time(),
            "consumed": False
        }
        _save_tokens(tokens)
        return token

    def verify_and_consume_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verifies token and consumes it so it can never be used twice."""
        if not token:
            return None
        tokens = _load_tokens()
        data = tokens.get(token)
        if not data or data.get("consumed"):
            return None
        data["consumed"] = True
        _save_tokens(tokens)
        return data

# Singleton engine instance
sql_engine = LlmPolicySqlEngine()
