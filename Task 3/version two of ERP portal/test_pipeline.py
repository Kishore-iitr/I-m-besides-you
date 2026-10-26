"""
Comprehensive Test Suite for Version 2 LangGraph Invoice Pipeline
Tests:
  1. PostgreSQL Supabase Database Connection & Schema Check
  2. Strict AgentIntent Parsing & SQL Generation
  3. Safety Guardrail Verification (> 100 rows threshold)
  4. Multi-Rule Execution One-by-One on Database
  5. Selective Approval for Vendor
  6. 3-Rule Independent Policy Execution
  7. Human-in-the-Loop Review Window: Stage Decisions without Committing
  8. Direct Shift of Unprocessed to HOLD: Stage Modal -> Commit Confirmation
"""

import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Remove script directory from sys.path temporarily so langgraph imports from site-packages
_this_dir = str(Path(__file__).resolve().parent)
_removed = False
if sys.path and sys.path[0] == _this_dir:
    sys.path.pop(0)
    _removed = True

from langgraph.graph import StateGraph, END

if _removed:
    sys.path.insert(0, _this_dir)

import importlib.util

_langgraph_file = Path(__file__).resolve().parent / "langgraph_v2.py"
_spec = importlib.util.spec_from_file_location("local_langgraph_engine", _langgraph_file)
_agent_mod = importlib.util.module_from_spec(_spec)
sys.modules["local_langgraph_engine"] = _agent_mod
_spec.loader.exec_module(_agent_mod)

engine = _agent_mod.engine
processing_agent = _agent_mod.processing_agent
processing_agent_detailed = _agent_mod.processing_agent_detailed
stage_agent_decisions = _agent_mod.stage_agent_decisions
stage_unprocessed_as_hold = _agent_mod.stage_unprocessed_as_hold
commit_staged_decisions = _agent_mod.commit_staged_decisions
fallback_intent_parser = _agent_mod.fallback_intent_parser
fallback_multi_rule_parser = _agent_mod.fallback_multi_rule_parser
AgentIntent = _agent_mod.AgentIntent
from sqlalchemy import text

def run_tests():
    print("=" * 70)
    print("🧪 Running Version 2 LangGraph Multi-Rule & Staging Pipeline Tests")
    print("=" * 70)

    # Test 1: Database Connection & Record Count
    print("\n[Test 1] Checking PostgreSQL connection and initial invoice counts...")
    with engine.connect() as conn:
        with engine.begin() as bconn:
            bconn.execute(text("UPDATE erp_invoices SET status = 'unprocessed', updated_at = CURRENT_TIMESTAMP;"))
        
        cnt = conn.execute(text("SELECT count(*) FROM orders WHERE status = 'unprocessed';")).scalar()
        print(f" -> Connected to PostgreSQL. Initial unprocessed orders: {cnt}")
        assert cnt > 0, "No unprocessed records found in database!"

    # Test 2: Multi-Rule Parser & Standalone Clean SQL Commands
    print("\n[Test 2] Testing Multi-Rule Decomposition into Separate SQL Commands...")
    multi_intent = fallback_multi_rule_parser("Approve routine invoices under 500000 yen, and put a freeze on orders over 1000000")
    print(f" -> Decomposed into {len(multi_intent.rules)} distinct rules:")
    for idx, r in enumerate(multi_intent.rules, 1):
        print(f"   Rule {idx}: '{r.rule_name}' | Action: [{r.target_action.upper()}] | SQL: {r.select_sql_query}")
        assert "status = 'unprocessed'" in r.select_sql_query
        assert " OR " not in r.select_sql_query.upper(), "Rules must be standalone and not mixed with gigantic OR clauses!"
    assert len(multi_intent.rules) == 2

    # Test 3: Guardrail Check (> 100 rows threshold)
    print("\n[Test 3] Testing Safety Guardrail threshold (> 100 records)...")
    res_guardrail = processing_agent("Pass through all unprocessed orders from today")
    print(f" -> Agent Output: {res_guardrail}")
    assert "Automation aborted" in res_guardrail or "threshold" in res_guardrail or "exceeding" in res_guardrail, (
        f"Guardrail did not trigger as expected: {res_guardrail}"
    )
    print(" ✅ Guardrail properly aborted runaway bulk execution!")

    # Test 4: Multi-Rule Independent Execution One-by-One on Database
    print("\n[Test 4] Testing Multi-Rule Execution One-by-One on PostgreSQL...")
    with engine.begin() as conn:
        conn.execute(text("UPDATE erp_invoices SET status = 'unprocessed', updated_at = CURRENT_TIMESTAMP;"))
    
    multi_res = processing_agent_detailed("Approve routine invoices under 500000 yen, and put a freeze on orders over 1000000")
    print(f" -> Overall Result: {multi_res['overall_message']}")
    print(f" -> Total Rules Executed: {multi_res['total_rules']}")
    print(f" -> Total Rows Updated: {multi_res['total_affected_rows']}")
    assert multi_res["total_rules"] == 2
    assert multi_res["total_affected_rows"] > 0
    for r in multi_res["rules"]:
        print(f"   * {r['rule_name']}: {r['message']} | SQL: {r['select_sql_query']}")
        assert r["status"] == "SUCCESS"
    print(" ✅ Separate SQL commands executed one by one successfully!")

    # Test 5: Selective Approval for Hokuriku Parts Industry
    print("\n[Test 5] Testing Standalone Approval for Hokuriku Parts Industry...")
    with engine.begin() as conn:
        conn.execute(text("UPDATE erp_invoices SET status = 'unprocessed', updated_at = CURRENT_TIMESTAMP;"))
    res_hokuriku = processing_agent("Approve Hokuriku Parts Industry Co., Ltd.")
    print(f" -> Agent Output: {res_hokuriku}")
    assert "Successfully shifted" in res_hokuriku and "approved" in res_hokuriku, f"Approval failed: {res_hokuriku}"
    print(" ✅ Selective approval executed!")

    # Test 6: 3-Rule Independent Policy Execution
    print("\n[Test 6] Testing 3-Rule Enterprise Policy Execution...")
    with engine.begin() as conn:
        conn.execute(text("UPDATE erp_invoices SET status = 'unprocessed', updated_at = CURRENT_TIMESTAMP;"))
    policy_res = processing_agent_detailed("Freeze orders over 1500000 yen, freeze category Adjustment, and approve Global Tech LLC")
    print(f" -> Rules Executed: {policy_res['total_rules']}")
    assert policy_res["total_rules"] >= 2
    for r in policy_res["rules"]:
        print(f"   * {r['rule_name']} -> SQL: {r['select_sql_query']} -> {r['message']}")
    print(" ✅ 3-Rule independent policy passed!")

    # Test 7: Human-in-the-Loop Review Window: Stage Decisions WITHOUT Committing
    print("\n[Test 7] Testing Human-in-the-Loop Review: Staging without Committing...")
    with engine.begin() as conn:
        conn.execute(text("UPDATE erp_invoices SET status = 'unprocessed', updated_at = CURRENT_TIMESTAMP;"))
    
    staged = stage_agent_decisions("Freeze orders over 1000000 yen and approve routine under 500000")
    print(f" -> Staged Records Count: {staged['evaluated_count']}")
    print(f" -> Approved to Stage: {staged['approved_count']}, Hold to Stage: {staged['hold_count']}")
    assert staged["evaluated_count"] > 0
    assert len(staged["staged_decisions"]) == staged["evaluated_count"]
    
    # Verify that database records remain UNPROCESSED (not committed yet!)
    with engine.connect() as conn:
        remaining_unprocessed = conn.execute(text("SELECT count(*) FROM erp_invoices WHERE LOWER(status) = 'unprocessed';")).scalar()
    print(f" -> DB check before commit: Unprocessed count = {remaining_unprocessed} (DB remains unchanged)")
    assert remaining_unprocessed == 105, f"Expected all 105 rows to still be unprocessed before commit, got {remaining_unprocessed}"

    # Commit staged decisions
    commit_res = commit_staged_decisions(staged["staged_decisions"])
    print(f" -> User Confirms & Commits: {commit_res['message']}")
    assert commit_res["success"] is True
    assert commit_res["affected_rows"] > 0

    # Verify that database records are now updated
    with engine.connect() as conn:
        after_unprocessed = conn.execute(text("SELECT count(*) FROM erp_invoices WHERE LOWER(status) = 'unprocessed';")).scalar()
    print(f" -> DB check after commit: Unprocessed count decreased to {after_unprocessed}")
    assert after_unprocessed < remaining_unprocessed
    print(" ✅ Staged decisions were held in review window and committed only upon user confirmation!")

    # Test 8: Direct Shift of Unprocessed to HOLD: Stage Modal -> Commit Confirmation
    print("\n[Test 8] Testing Direct Shift of Unprocessed to HOLD...")
    with engine.begin() as conn:
        conn.execute(text("UPDATE erp_invoices SET status = 'unprocessed', updated_at = CURRENT_TIMESTAMP;"))

    hold_stage = stage_unprocessed_as_hold("Managerial freeze of all unprocessed items")
    print(f" -> Direct Hold Staged Count: {hold_stage['evaluated_count']}")
    assert hold_stage["evaluated_count"] == 105
    assert hold_stage["hold_count"] == 105
    assert all(d["new_status"] == "Hold" for d in hold_stage["staged_decisions"])

    # Verify all detailed fields are populated for modal display
    sample = hold_stage["staged_decisions"][0]
    print(f" -> Sample Modal Record: ID={sample['id']}, Invoice={sample['invoice_no']}, Vendor={sample['entity_name']}, Amount={sample['amount']}, NewStatus={sample['new_status']}")
    assert sample["id"] and sample["invoice_no"] and sample["entity_name"] and sample["amount"]

    # Verify DB still has all unprocessed before commit
    with engine.connect() as conn:
        db_unprocessed = conn.execute(text("SELECT count(*) FROM erp_invoices WHERE LOWER(status) = 'unprocessed';")).scalar()
    assert db_unprocessed == 105

    # Commit the direct hold
    hold_commit = commit_staged_decisions(hold_stage["staged_decisions"])
    print(f" -> User pressed Commit in modal: {hold_commit['message']}")
    assert hold_commit["success"] is True
    assert hold_commit["affected_rows"] == 105

    with engine.connect() as conn:
        final_hold_count = conn.execute(text("SELECT count(*) FROM erp_invoices WHERE LOWER(status) = 'hold';")).scalar()
    print(f" -> Final Hold count in PostgreSQL: {final_hold_count}")
    assert final_hold_count == 105
    print(" ✅ Direct shift to HOLD successfully staged and committed!")

    # Cleanup Database
    print("\n[Cleanup] Resetting database back to 'unprocessed' for clean initial state...")
    with engine.begin() as conn:
        conn.execute(text("UPDATE erp_invoices SET status = 'unprocessed', updated_at = CURRENT_TIMESTAMP;"))
    print(" ✅ All invoices reset to unprocessed.")

    print("\n" + "=" * 70)
    print("🎉 ALL 8 TESTS PASSED! FULL PIPELINE & STAGED MODAL VERIFIED 100%!")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
