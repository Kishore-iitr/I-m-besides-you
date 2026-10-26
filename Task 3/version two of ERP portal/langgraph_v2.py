"""
LangGraph Multi-Rule AI Routing Agent & Safe Database Pipeline (Version 2)
Enterprise Invoice & Order Processing Architecture with Human-in-the-Loop Staging

Features:
  1. Decomposes user instructions & policies into SEPARATE, INDEPENDENT rules.
  2. Each rule has its own clean, standalone, readable SQL command.
  3. Executes each independent SQL command ONE BY ONE on the PostgreSQL database.
  4. Per-rule safety guardrail (<= 100 records limit).
  5. Human-in-the-loop Staging & Pre-commit Confirmation:
     - Unprocessed records identified for HOLD or APPROVAL are staged first with full details.
     - Changes are only committed to the database when the user explicitly confirms.
"""

import os
import re
import sys
from pathlib import Path
from typing import Literal, List, Dict, Any, Optional, TypedDict
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text, URL

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from langgraph.graph import StateGraph, END

# Load environment configuration (.env)
ENV_PATH = Path(__file__).resolve().parent / ".env"
PARENT_ENV = Path(__file__).resolve().parent.parent / ".env"

if ENV_PATH.exists():
    from dotenv import load_dotenv
    load_dotenv(ENV_PATH)
elif PARENT_ENV.exists():
    from dotenv import load_dotenv
    load_dotenv(PARENT_ENV)

# ------------------------------------------------------------------------------
# 1. Database Connection (PostgreSQL with SQLite Fallback)
# ------------------------------------------------------------------------------
def get_database_engine():
    """Initializes SQLAlchemy Engine pointing to PostgreSQL or local SQLite."""
    pg_host = os.getenv("DB_POSTGRESDB_HOST")
    pg_user = os.getenv("DB_POSTGRESDB_USER")
    pg_pass = os.getenv("DB_POSTGRESDB_PASSWORD")
    pg_db = os.getenv("DB_POSTGRESDB_DATABASE", "postgres")
    pg_port = os.getenv("DB_POSTGRESDB_PORT", "5432")
    db_url_env = os.getenv("DATABASE_URL")

    if db_url_env:
        try:
            eng = create_engine(db_url_env, connect_args={"connect_timeout": 5})
            with eng.connect() as conn:
                conn.execute(text("SELECT 1;"))
            return eng
        except Exception:
            pass

    if pg_host and pg_user and pg_pass:
        try:
            url_obj = URL.create(
                drivername="postgresql+psycopg2",
                username=pg_user,
                password=pg_pass,
                host=pg_host,
                port=int(pg_port) if str(pg_port).isdigit() else 5432,
                database=pg_db
            )
            eng = create_engine(url_obj, connect_args={"connect_timeout": 8})
            with eng.connect() as conn:
                conn.execute(text("SELECT 1;"))
            print(f"[langgraph.py] Connected to PostgreSQL at {pg_host}")
            return eng
        except Exception as e:
            print(f"[langgraph.py] PostgreSQL connection error: {e}. Falling back to SQLite.")

    # SQLite Fallback
    sqlite_file = Path(__file__).resolve().parent.parent / "erp_invoices.db"
    if not sqlite_file.exists():
        sqlite_file = Path(__file__).resolve().parent / "erp_invoices.db"
    sqlite_url = f"sqlite:///{sqlite_file.as_posix()}"
    print(f"[langgraph.py] Using local SQLite: {sqlite_url}")
    return create_engine(sqlite_url)

engine = get_database_engine()

# Ensure orders view exists on PostgreSQL if not already present
try:
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text("""
                CREATE OR REPLACE VIEW orders AS 
                SELECT 
                    id, 
                    name AS customer_name, 
                    updated_at::date AS order_date, 
                    raw_amount AS total_amount, 
                    status,
                    invoice_no,
                    employee_id,
                    type,
                    amount,
                    comment
                FROM erp_invoices;
            """))
except Exception:
    pass

# ------------------------------------------------------------------------------
# 2. Strict Output Schema: Independent Discrete Rules
# ------------------------------------------------------------------------------
class SingleRuleIntent(BaseModel):
    rule_id: str = Field(default="rule_1", description="Identifier like rule_1, rule_2")
    rule_name: str = Field(description="Clear, concise, human-readable rule title (e.g. 'Rule 1: High Value Freeze > 1,000,000')")
    target_action: Literal["approved", "hold"] = Field(
        description="The action to apply. Must strictly be 'approved' or 'hold'."
    )
    select_sql_query: str = Field(
        description="A clean, simple, standalone SQL query that selects only 'id' from 'orders' where status = 'unprocessed' for this rule only. Do NOT combine multiple conditions with OR into a giant query."
    )
    rationale: str = Field(default="", description="Brief explanation of why this rule was created and which records it targets.")

class MultiRuleAgentIntent(BaseModel):
    rules: List[SingleRuleIntent] = Field(
        description="List of separate, independent rules. Each rule contains its own clean SQL command."
    )

AgentIntent = SingleRuleIntent

# ------------------------------------------------------------------------------
# 3. LLM Setup (ChatOpenAI with Deterministic Multi-Rule Fallback)
# ------------------------------------------------------------------------------
openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()

try:
    from langchain_openai import ChatOpenAI
    if openai_api_key:
        llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o"), temperature=0)
        structured_llm = llm.with_structured_output(MultiRuleAgentIntent)
    else:
        structured_llm = None
except Exception:
    structured_llm = None

DB_SCHEMA_CONTEXT = """
Table name: orders (alias: erp_invoices)
Columns:
  - id (VARCHAR/INT, Primary Key)
  - customer_name (VARCHAR)
  - order_date (DATE)
  - total_amount (NUMERIC/BIGINT)
  - type (VARCHAR) -> 'Routine', 'Adjustment', 'Spot'
  - status (VARCHAR) -> Initial state is 'unprocessed'. Can be changed to 'approved' or 'hold'.
"""

SYSTEM_INSTRUCTION = f"""
You are an expert corporate accounting and database management routing agent.
Analyze the user's request and decompose it into SEPARATE, INDEPENDENT rules.

CRITICAL ARCHITECTURE RULES:
1. Do NOT mix multiple distinct criteria into a single gigantic SQL query with nested OR clauses.
2. For each distinct policy or criteria, generate a SEPARATE rule with its own clean SQL command.
   - Example Rule 1: High value freeze (> 1,000,000) -> separate SQL SELECT
   - Example Rule 2: Routine low value approval (< 500,000) -> separate SQL SELECT
   - Example Rule 3: Category adjustment freeze -> separate SQL SELECT
3. Each generated query must ONLY select the 'id' column from 'orders'.
4. Each query must explicitly include `WHERE status = 'unprocessed'` along with rule-specific filters.
5. Target action must strictly be 'approved' or 'hold'.

Database Schema:
{DB_SCHEMA_CONTEXT}
"""

def fallback_multi_rule_parser(user_prompt: str) -> MultiRuleAgentIntent:
    """
    Deterministic rule engine that parses natural language or policy text
    into clean, independent rules, each with its own standalone SQL command.
    """
    prompt_lower = user_prompt.lower()
    rules: List[SingleRuleIntent] = []
    rule_counter = 1

    # Check for High Amount Limit Freeze / Hold (e.g., > 1,000,000 or > 1,500,000)
    amt_over_match = re.search(r'(?:freeze|hold|review|stop|over|above|>|\$|¥)\s*([0-9,]+)', user_prompt, re.IGNORECASE)
    has_hold_intent = any(k in prompt_lower for k in ["hold", "freeze", "stop", "pause", "reject", "review", "保留", "上限", "超過"])

    # Scenario A: Specific High-Value Freeze Rule
    if amt_over_match and has_hold_intent:
        val = amt_over_match.group(1).replace(",", "")
        if val.isdigit() and int(val) > 1000:
            rules.append(SingleRuleIntent(
                rule_id=f"rule_{rule_counter}",
                rule_name=f"Rule {rule_counter}: Freeze High-Value Invoices (> ¥{int(val):,})",
                target_action="hold",
                select_sql_query=f"SELECT id FROM orders WHERE status = 'unprocessed' AND total_amount > {val}",
                rationale=f"High-value invoices exceeding ¥{int(val):,} require manual managerial authorization."
            ))
            rule_counter += 1

    # Scenario B: Category Adjustment / Spot Freeze Rule
    if any(c in prompt_lower for c in ["adjustment", "spot", "変動", "調整"]):
        rules.append(SingleRuleIntent(
            rule_id=f"rule_{rule_counter}",
            rule_name=f"Rule {rule_counter}: Freeze Adjustment & Spot Invoices",
            target_action="hold",
            select_sql_query="SELECT id FROM orders WHERE status = 'unprocessed' AND type IN ('Adjustment', 'Spot')",
            rationale="Adjustment and Spot transactions involve variable fees and require audit scrutiny."
        ))
        rule_counter += 1

    # Scenario C: Low-Value Routine Approvals (e.g., < 500,000 or routine)
    amt_under_match = re.search(r'(?:under|below|less than|<)\s*([0-9,]+)', user_prompt, re.IGNORECASE)
    if "routine" in prompt_lower or amt_under_match:
        val = amt_under_match.group(1).replace(",", "") if amt_under_match else "500000"
        if val.isdigit():
            rules.append(SingleRuleIntent(
                rule_id=f"rule_{rule_counter}",
                rule_name=f"Rule {rule_counter}: Approve Routine Invoices (< ¥{int(val):,})",
                target_action="approved",
                select_sql_query=f"SELECT id FROM orders WHERE status = 'unprocessed' AND type = 'Routine' AND total_amount < {val}",
                rationale=f"Routine operational invoices under ¥{int(val):,} comply with standard procurement terms."
            ))
            rule_counter += 1

    # Scenario D: Specific Vendor Approval Rules
    known_vendors = [
        ("Global Tech LLC", "Global Tech LLC Recurring Maintenance"),
        ("Hokuriku Parts Industry Co., Ltd.", "Hokuriku Parts Industry Fixed Contract"),
        ("Yamato Shoji Co., Ltd.", "Yamato Shoji Administrative Contract"),
        ("Yamada Manufacturing Co., Ltd.", "Yamada Manufacturing Fixed Fee"),
        ("Tokyo Cloud Solutions", "Tokyo Cloud Solutions SaaS Fee")
    ]
    for v_name, v_desc in known_vendors:
        if v_name.lower() in prompt_lower or v_name.split()[0].lower() in prompt_lower:
            rules.append(SingleRuleIntent(
                rule_id=f"rule_{rule_counter}",
                rule_name=f"Rule {rule_counter}: Approve {v_desc}",
                target_action="approved",
                select_sql_query=f"SELECT id FROM orders WHERE status = 'unprocessed' AND customer_name = '{v_name}'",
                rationale=f"Vendor contract terms for {v_name} are verified against the master ledger."
            ))
            rule_counter += 1

    # Fallback if no specific rule detected: Generate single clean command matching primary intent
    if not rules:
        action: Literal["approved", "hold"] = "hold" if has_hold_intent else "approved"
        action_title = "Freeze All Unprocessed Records" if action == "hold" else "Approve Unprocessed Records"
        rules.append(SingleRuleIntent(
            rule_id="rule_1",
            rule_name=f"Rule 1: {action_title}",
            target_action=action,
            select_sql_query="SELECT id FROM orders WHERE status = 'unprocessed'",
            rationale="Batch shift of unprocessed records for managerial review."
        ))

    return MultiRuleAgentIntent(rules=rules)

def fallback_intent_parser(user_prompt: str) -> SingleRuleIntent:
    multi = fallback_multi_rule_parser(user_prompt)
    return multi.rules[0]

# ------------------------------------------------------------------------------
# 4. LangGraph Multi-Rule StateGraph Workflow with Staging
# ------------------------------------------------------------------------------
class RuleExecutionDetail(TypedDict):
    rule_id: str
    rule_name: str
    target_action: str
    select_sql_query: str
    rationale: str
    target_ids: List[Any]
    target_count: int
    affected_rows: int
    status: str          # 'SUCCESS', 'GUARDRAIL_ABORTED', 'NO_RECORDS', 'ERROR', 'STAGED'
    message: str

class MultiRuleState(TypedDict):
    user_prompt: str
    auto_commit: bool
    rules: List[SingleRuleIntent]
    current_rule_index: int
    rule_results: List[RuleExecutionDetail]
    staged_decisions: List[Dict[str, Any]]
    total_affected_rows: int
    step_logs: List[str]
    overall_message: str
    error: Optional[str]

def node_parse_rules(state: MultiRuleState) -> Dict[str, Any]:
    """Node 1: Parse user prompt into distinct, independent rules."""
    user_prompt = state["user_prompt"]
    logs = list(state.get("step_logs", []))
    logs.append(f"📥 [Step 1: Parse Rules] Analyzing prompt: \"{user_prompt}\"")

    parsed_multi = None
    if structured_llm:
        messages = [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": user_prompt}
        ]
        try:
            parsed_multi = structured_llm.invoke(messages)
            logs.append(f"🤖 [Step 1: LLM] Decomposed request into {len(parsed_multi.rules)} independent rules using OpenAI gpt-4o")
        except Exception as e:
            logs.append(f"⚠️ [Step 1: LLM Warning] ({e}). Using deterministic multi-rule generator.")
            parsed_multi = fallback_multi_rule_parser(user_prompt)
    else:
        logs.append("⚡ [Step 1: Rule Engine] Decomposing request into separate rules")
        parsed_multi = fallback_multi_rule_parser(user_prompt)

    for idx, r in enumerate(parsed_multi.rules, 1):
        logs.append(f"   📜 Rule {idx}: \"{r.rule_name}\" -> Action: [{r.target_action.upper()}] | SQL: {r.select_sql_query}")

    return {
        "rules": parsed_multi.rules,
        "current_rule_index": 0,
        "rule_results": [],
        "staged_decisions": [],
        "total_affected_rows": 0,
        "step_logs": logs
    }

def node_execute_current_rule(state: MultiRuleState) -> Dict[str, Any]:
    """
    Node 2: Executes a SINGLE independent rule on the PostgreSQL database.
    If auto_commit is False: Stages all record details for human-in-the-loop modal confirmation.
    If auto_commit is True: Directly updates the database.
    """
    rules = state["rules"]
    idx = state["current_rule_index"]
    rule = rules[idx]
    logs = list(state["step_logs"])
    results = list(state.get("rule_results", []))
    staged = list(state.get("staged_decisions", []))
    total_affected = state.get("total_affected_rows", 0)
    auto_commit = state.get("auto_commit", True)

    logs.append(f"\n▶️ [Executing Rule {idx + 1}/{len(rules)}] {rule.rule_name}")
    logs.append(f"   💻 Standalone SQL: {rule.select_sql_query}")

    # Normalize status matching to be resilient to 'unprocessed', 'Unprocessed', and '未処理'
    exec_sql = re.sub(
        r"\bstatus\s*=\s*'unprocessed'",
        "(LOWER(status) = 'unprocessed' OR status = '未処理')",
        rule.select_sql_query,
        flags=re.IGNORECASE
    )

    # 1. Execute Independent SELECT Search
    try:
        with engine.connect() as conn:
            search_results = conn.execute(text(exec_sql)).fetchall()
            target_ids = [row[0] for row in search_results]
    except Exception as e:
        err_msg = f"❌ SQL execution failed for {rule.rule_name}: {str(e)}"
        logs.append(f"   {err_msg}")
        results.append({
            "rule_id": rule.rule_id,
            "rule_name": rule.rule_name,
            "target_action": rule.target_action,
            "select_sql_query": rule.select_sql_query,
            "rationale": rule.rationale,
            "target_ids": [],
            "target_count": 0,
            "affected_rows": 0,
            "status": "ERROR",
            "message": err_msg
        })
        return {
            "current_rule_index": idx + 1,
            "rule_results": results,
            "staged_decisions": staged,
            "step_logs": logs
        }

    # 2. Check If Records Matched
    if not target_ids:
        no_rec_msg = f"ℹ️ Rule {idx + 1}: Found 0 'unprocessed' records matching this specific rule."
        logs.append(f"   {no_rec_msg}")
        results.append({
            "rule_id": rule.rule_id,
            "rule_name": rule.rule_name,
            "target_action": rule.target_action,
            "select_sql_query": rule.select_sql_query,
            "rationale": rule.rationale,
            "target_ids": [],
            "target_count": 0,
            "affected_rows": 0,
            "status": "NO_RECORDS",
            "message": no_rec_msg
        })
        return {
            "current_rule_index": idx + 1,
            "rule_results": results,
            "staged_decisions": staged,
            "step_logs": logs
        }

    logs.append(f"   🔍 Rule {idx + 1}: Found {len(target_ids)} matching rows. IDs: {target_ids[:4]}...")

    # 3. Safety Guardrail Check for this Rule
    if len(target_ids) > 100:
        guard_msg = f"⚠️ Rule {idx + 1} aborted: Matches {len(target_ids)} rows, exceeding safety threshold (max 100)."
        logs.append(f"   ⛔ {guard_msg}")
        results.append({
            "rule_id": rule.rule_id,
            "rule_name": rule.rule_name,
            "target_action": rule.target_action,
            "select_sql_query": rule.select_sql_query,
            "rationale": rule.rationale,
            "target_ids": target_ids,
            "target_count": len(target_ids),
            "affected_rows": 0,
            "status": "GUARDRAIL_ABORTED",
            "message": guard_msg
        })
        return {
            "current_rule_index": idx + 1,
            "rule_results": results,
            "staged_decisions": staged,
            "step_logs": logs
        }

    # 4. Fetch Full Metadata for Staging & Human Review Modal
    id_placeholders = []
    for tid in target_ids:
        clean_tid = str(tid).replace("'", "''")
        id_placeholders.append(f"'{clean_tid}'")
    in_clause = ", ".join(id_placeholders)

    detail_sql = f"""
        SELECT id, invoice_no, name, raw_amount, amount, type, status, ref, comment
        FROM erp_invoices
        WHERE id IN ({in_clause}) OR invoice_no IN ({in_clause});
    """

    try:
        with engine.connect() as conn:
            detail_rows = conn.execute(text(detail_sql)).fetchall()

        staged_items = []
        for r in detail_rows:
            staged_items.append({
                "id": str(r[0]),
                "invoice_no": str(r[1] or r[0]),
                "entity_name": str(r[2] or "Unknown Vendor"),
                "raw_amount": r[3] or 0,
                "amount": r[4] or (f"¥{r[3]:,}" if r[3] else "¥0"),
                "type": r[5] or "Routine",
                "current_status": r[6] or "unprocessed",
                "new_status": "Hold" if rule.target_action.lower() == "hold" else "Approved",
                "matched_rule_id": rule.rule_id,
                "matched_rule_summary": rule.rule_name,
                "reasons": [rule.rationale] if rule.rationale else ["Policy threshold rule matched"],
                "ref": str(r[7] or ""),
                "comment": f"[{rule.target_action.upper()}] {rule.rule_name}"
            })

        # Append to staged decisions (deduplicating by ID, latest action wins)
        existing_ids = {d["id"]: i for i, d in enumerate(staged)}
        for item in staged_items:
            if item["id"] in existing_ids:
                staged[existing_ids[item["id"]]] = item
            else:
                existing_ids[item["id"]] = len(staged)
                staged.append(item)

    except Exception as e:
        logs.append(f"   ⚠️ Could not fetch full row details: {e}")

    # 5. Execute or Stage
    if not auto_commit:
        # Human-in-the-loop Staging Mode: do NOT execute UPDATE yet
        stage_msg = f"⚡ Rule {idx + 1}: Staged {len(target_ids)} row(s) to '{rule.target_action.upper()}'. Awaiting confirmation modal."
        logs.append(f"   {stage_msg}")
        results.append({
            "rule_id": rule.rule_id,
            "rule_name": rule.rule_name,
            "target_action": rule.target_action,
            "select_sql_query": rule.select_sql_query,
            "rationale": rule.rationale,
            "target_ids": target_ids,
            "target_count": len(target_ids),
            "affected_rows": 0,
            "status": "STAGED",
            "message": stage_msg
        })
        return {
            "current_rule_index": idx + 1,
            "rule_results": results,
            "staged_decisions": staged,
            "total_affected_rows": total_affected,
            "step_logs": logs
        }

    # Direct Commit Mode (auto_commit == True)
    update_query = text(f"""
        UPDATE orders 
        SET status = :new_status 
        WHERE id IN ({in_clause}) 
          AND (LOWER(status) = 'unprocessed' OR status = '未処理');
    """)

    try:
        with engine.begin() as conn:
            res = conn.execute(update_query, {"new_status": rule.target_action})
            affected = res.rowcount

        success_msg = f"✅ Rule {idx + 1}: Successfully shifted {affected} rows to '{rule.target_action}'."
        logs.append(f"   {success_msg}")
        results.append({
            "rule_id": rule.rule_id,
            "rule_name": rule.rule_name,
            "target_action": rule.target_action,
            "select_sql_query": rule.select_sql_query,
            "rationale": rule.rationale,
            "target_ids": target_ids,
            "target_count": len(target_ids),
            "affected_rows": affected,
            "status": "SUCCESS",
            "message": success_msg
        })
        return {
            "current_rule_index": idx + 1,
            "rule_results": results,
            "staged_decisions": staged,
            "total_affected_rows": total_affected + affected,
            "step_logs": logs
        }
    except Exception as e:
        tx_err = f"❌ Transaction update failed for Rule {idx + 1}: {str(e)}"
        logs.append(f"   {tx_err}")
        results.append({
            "rule_id": rule.rule_id,
            "rule_name": rule.rule_name,
            "target_action": rule.target_action,
            "select_sql_query": rule.select_sql_query,
            "rationale": rule.rationale,
            "target_ids": target_ids,
            "target_count": len(target_ids),
            "affected_rows": 0,
            "status": "ERROR",
            "message": tx_err
        })
        return {
            "current_rule_index": idx + 1,
            "rule_results": results,
            "staged_decisions": staged,
            "step_logs": logs
        }

def route_next_rule(state: MultiRuleState) -> str:
    """Routes to the next rule in sequence, or to summarize when all finished."""
    if state["current_rule_index"] < len(state["rules"]):
        return "execute_current_rule"
    return "summarize_results"

def node_summarize_results(state: MultiRuleState) -> Dict[str, Any]:
    """Node 3: Aggregates summary of all independent rule executions."""
    logs = list(state["step_logs"])
    results = state.get("rule_results", [])
    total_affected = state.get("total_affected_rows", 0)
    staged = state.get("staged_decisions", [])
    auto_commit = state.get("auto_commit", True)

    success_rules = [r for r in results if r["status"] == "SUCCESS"]
    staged_rules = [r for r in results if r["status"] == "STAGED"]
    aborted_rules = [r for r in results if r["status"] == "GUARDRAIL_ABORTED"]
    empty_rules = [r for r in results if r["status"] == "NO_RECORDS"]

    summary_parts = []
    if not auto_commit and staged:
        summary_parts.append(f"⚡ {len(staged)} candidate record(s) staged across {len(staged_rules)} rule(s). Confirmation modal ready.")
    elif success_rules:
        summary_parts.append(f"✅ {len(success_rules)} rule(s) successfully executed ({total_affected} total rows updated)")
    
    if aborted_rules:
        summary_parts.append(f"⚠️ {len(aborted_rules)} rule(s) aborted by safety guardrail (>100 rows)")
    if empty_rules and not success_rules and not staged_rules:
        summary_parts.append("ℹ️ No 'unprocessed' records matched the rule criteria")

    overall_msg = ". ".join(summary_parts) if summary_parts else f"Evaluation completed for {len(results)} rule(s)."
    logs.append(f"\n🏁 [Execution Complete] {overall_msg}")

    return {
        "overall_message": overall_msg,
        "step_logs": logs
    }

# Assemble LangGraph Workflow
workflow = StateGraph(MultiRuleState)
workflow.add_node("parse_rules", node_parse_rules)
workflow.add_node("execute_current_rule", node_execute_current_rule)
workflow.add_node("summarize_results", node_summarize_results)

workflow.set_entry_point("parse_rules")
workflow.add_edge("parse_rules", "execute_current_rule")
workflow.add_conditional_edges("execute_current_rule", route_next_rule, {
    "execute_current_rule": "execute_current_rule",
    "summarize_results": "summarize_results"
})
workflow.add_edge("summarize_results", END)

agent_graph = workflow.compile()

# ------------------------------------------------------------------------------
# 5. Public Functions
# ------------------------------------------------------------------------------
def processing_agent(user_prompt: str) -> str:
    """
    Direct string entry point for tests and automated scripting.
    Executes independent SQL rules one by one, commits immediately, and returns summary string.
    """
    initial_state: MultiRuleState = {
        "user_prompt": user_prompt,
        "auto_commit": True,
        "rules": [],
        "current_rule_index": 0,
        "rule_results": [],
        "staged_decisions": [],
        "total_affected_rows": 0,
        "step_logs": [],
        "overall_message": "",
        "error": None
    }
    final_state = agent_graph.invoke(initial_state)
    results = final_state.get("rule_results", [])
    if len(results) == 1:
        return results[0]["message"]
    return final_state.get("overall_message", "Completed.")

def processing_agent_detailed(user_prompt: str, auto_commit: bool = True) -> Dict[str, Any]:
    """
    Detailed entry point returning structured results per rule.
    """
    initial_state: MultiRuleState = {
        "user_prompt": user_prompt,
        "auto_commit": auto_commit,
        "rules": [],
        "current_rule_index": 0,
        "rule_results": [],
        "staged_decisions": [],
        "total_affected_rows": 0,
        "step_logs": [],
        "overall_message": "",
        "error": None
    }
    final_state = agent_graph.invoke(initial_state)
    results = final_state.get("rule_results", [])
    staged = final_state.get("staged_decisions", [])

    return {
        "success": any(r["status"] in ("SUCCESS", "STAGED") for r in results) or not any(r["status"] == "ERROR" for r in results),
        "stage": "COMMITTED" if auto_commit else "STAGED",
        "overall_message": final_state.get("overall_message", ""),
        "total_rules": len(results),
        "total_affected_rows": final_state.get("total_affected_rows", 0),
        "evaluated_count": len(staged),
        "approved_count": sum(1 for d in staged if d.get("new_status", "").lower() in ("approved", "confirmed")),
        "hold_count": sum(1 for d in staged if d.get("new_status", "").lower() == "hold"),
        "staged_decisions": staged,
        "rules": results,
        "step_logs": final_state.get("step_logs", [])
    }

def stage_agent_decisions(user_prompt: str) -> Dict[str, Any]:
    """
    Human-in-the-Loop Staging Entry Point:
    Parses rules, runs independent SQL SELECT queries to find candidate records,
    collects full record details for modal presentation, but DOES NOT commit to DB.
    """
    return processing_agent_detailed(user_prompt, auto_commit=False)

def stage_unprocessed_as_hold(comment: str = "") -> Dict[str, Any]:
    """
    Directly stages all currently unprocessed records as HOLD for human review modal.
    Does not update the database until commit_staged_decisions is called.
    """
    sql = """
        SELECT id, invoice_no, name, raw_amount, amount, type, status, ref, comment
        FROM erp_invoices
        WHERE (LOWER(status) = 'unprocessed' OR status = '未処理')
        ORDER BY id ASC;
    """
    with engine.connect() as conn:
        rows = conn.execute(text(sql)).fetchall()

    staged = []
    default_comment = comment or "[HOLD] 未処理伝票一括保留・担当者精査要"
    for r in rows:
        staged.append({
            "id": str(r[0]),
            "invoice_no": str(r[1] or r[0]),
            "entity_name": str(r[2] or "Unknown Vendor"),
            "raw_amount": r[3] or 0,
            "amount": r[4] or (f"¥{r[3]:,}" if r[3] else "¥0"),
            "type": r[5] or "Routine",
            "current_status": r[6] or "unprocessed",
            "new_status": "Hold",
            "matched_rule_id": "HOLD_ALL",
            "matched_rule_summary": "Direct Shift: All Unprocessed to HOLD",
            "reasons": ["Unprocessed batch freeze for manual managerial review"],
            "ref": str(r[7] or ""),
            "comment": default_comment
        })

    rule_detail: RuleExecutionDetail = {
        "rule_id": "HOLD_ALL",
        "rule_name": "Rule 1: Direct Shift All Unprocessed to HOLD",
        "target_action": "hold",
        "select_sql_query": "SELECT id FROM orders WHERE status = 'unprocessed'",
        "rationale": "Direct freeze on all unprocessed records for manual managerial review.",
        "target_ids": [d["id"] for d in staged],
        "target_count": len(staged),
        "affected_rows": 0,
        "status": "STAGED",
        "message": f"Found {len(staged)} unprocessed record(s) staged for HOLD."
    }

    return {
        "success": True,
        "stage": "STAGED",
        "user_prompt": "Put all unprocessed records on hold",
        "total_rules": 1,
        "evaluated_count": len(staged),
        "approved_count": 0,
        "hold_count": len(staged),
        "staged_decisions": staged,
        "rules": [rule_detail],
        "step_logs": [
            "📥 [Direct Hold Action] Querying all unprocessed records...",
            f"🔍 Found {len(staged)} unprocessed records.",
            f"⚡ Staged {len(staged)} records for user confirmation window."
        ],
        "overall_message": f"{len(staged)} unprocessed record(s) staged for HOLD. Waiting for user commit."
    }

def commit_staged_decisions(decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Executes actual SQL UPDATE transactions in PostgreSQL for user-confirmed decisions.
    Groups decisions by (new_status, comment) for high-performance atomic execution.
    """
    if not decisions:
        return {"success": True, "stage": "COMMITTED", "affected_rows": 0, "message": "No decisions to commit."}

    # Group decisions by (new_status, comment) for fast atomic execution
    groups: Dict[tuple, List[str]] = {}
    for d in decisions:
        new_st = str(d.get("new_status", "hold")).lower()
        com = str(d.get("comment", "") or "")
        rec_id = str(d.get("id"))
        key = (new_st, com)
        if key not in groups:
            groups[key] = []
        groups[key].append(rec_id)

    affected_total = 0
    with engine.begin() as conn:
        for (new_st, com), ids in groups.items():
            id_placeholders = []
            for tid in ids:
                clean_tid = tid.replace("'", "''")
                id_placeholders.append(f"'{clean_tid}'")
            in_clause = ", ".join(id_placeholders)

            update_sql = f"""
                UPDATE erp_invoices 
                SET status = :new_status, comment = :comment, updated_at = CURRENT_TIMESTAMP
                WHERE (id IN ({in_clause}) OR invoice_no IN ({in_clause}));
            """
            res = conn.execute(text(update_sql), {"new_status": new_st, "comment": com})
            affected_total += res.rowcount

    return {
        "success": True,
        "stage": "COMMITTED",
        "affected_rows": affected_total,
        "message": f"✅ Successfully committed {affected_total} records to the database."
    }

# ------------------------------------------------------------------------------
# Verification Trigger Block
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    print("Testing Multi-Rule LangGraph Agent with Staging...")
    test_prompt = "Approve routine invoices under 500000 yen, and put a freeze on orders over 1000000"
    print(f"\nUser Prompt: \"{test_prompt}\"")
    
    # 1. Test Staging Mode (Dry Run / Human-in-the-Loop)
    staged = stage_agent_decisions(test_prompt)
    print(f"\n[Staging Mode] Evaluated: {staged['evaluated_count']}, Approved: {staged['approved_count']}, Hold: {staged['hold_count']}")
    print(f"Staged Decisions Count: {len(staged['staged_decisions'])}")
    if staged['staged_decisions']:
        sample = staged['staged_decisions'][0]
        print(f"Sample Staged Record: ID={sample['id']}, Vendor={sample['entity_name']}, Amount={sample['amount']}, NewStatus={sample['new_status']}")
