# -*- coding: utf-8 -*-
"""
verify_zero_hardcoding.py
Tests that both the English sample policy and completely arbitrary unseen policies
are parsed dynamically into pristine ANSI SQL rules with zero hardcoding.
"""
from copilot_langgraph_engine import copilot_engine

def test_english_sample():
    print("=" * 60)
    print("TEST 1: Standard English 4-Rule Policy")
    print("=" * 60)
    doc_text = """Rule 1 — Vendor Registration

The following vendor codes are registered: V3001, V3002, V3004, V3005, V3006, V3007, V3008, V3009, V3010, V3011, and V3012.

Hold any voucher whose vendor code is not on this list.

Rule 2 — Adjustment Review

Hold every voucher with category Adjustment, regardless of amount or vendor. Manual finance review is mandatory.

Rule 3 — High-Value Review

Hold every voucher whose amount is strictly greater than ¥1,800,000. This rule applies to all vendors, including registered vendors and invoices whose amounts appear in their contracts.

An amount equal to ¥1,800,000 does not trigger this rule.

Rule 4 — Routine Approval

Approve a voucher only if:

The vendor code is registered.

The category is Routine.

The amount is ¥1,800,000 or less.

No mandatory Hold rule applies.

Exact contract-amount matching is not required under this policy."""

    res = copilot_engine.analyze_policy("invoice", doc_text, "english_sample.txt")
    rules = res.get("rules", [])
    print(f"Extracted {len(rules)} rules:")
    for r in rules:
        print(f"  [{r.get('rule_id')}] {r.get('name')} -> Action: {r.get('action_on_match')}")
        print(f"       SQL: {r.get('sql_condition')}")

    # Assertions
    conds = [r.get("sql_condition") for r in rules]
    assert any("employee_id NOT IN" in c for c in conds), "Missing Rule 1 NOT IN condition"
    assert any("type = 'Adjustment'" in c for c in conds), "Missing Rule 2 category Adjustment condition"
    assert any("raw_amount > 1800000" in c for c in conds), "Missing Rule 3 raw_amount > 1800000"
    assert any("raw_amount <= 1800000" in c and "employee_id IN" in c for c in conds), "Missing Rule 4 Routine Approval condition"
    print("✓ TEST 1 PASSED: English 4-rule policy verified!")

def test_arbitrary_unseen_policy():
    print("\n" + "=" * 60)
    print("TEST 2: Completely Arbitrary Unseen Policy (Zero Hardcoding Test)")
    print("=" * 60)
    unseen_doc = """Rule 1 — Medical Supplier Registration
The following supplier codes are registered: M101, M102, and M105.
Hold any voucher whose supplier code is not on this list.

Rule 2 — Expedited Order Review
Hold every voucher with category Expedited, regardless of amount or supplier. Special clinical audit is required.

Rule 3 — Threshold Review
Hold every voucher whose amount is strictly greater than ¥350,000. This rule applies to all suppliers.
An amount equal to ¥350,000 does not trigger this rule.

Rule 4 — Standard Approval
Approve a voucher only if:
The supplier code is registered.
The category is Regular.
The amount is ¥350,000 or less.
No mandatory Hold rule applies."""

    res = copilot_engine.analyze_policy("invoice", unseen_doc, "arbitrary_policy.txt")
    rules = res.get("rules", [])
    print(f"Extracted {len(rules)} rules:")
    for r in rules:
        print(f"  [{r.get('rule_id')}] {r.get('name')} -> Action: {r.get('action_on_match')}")
        print(f"       SQL: {r.get('sql_condition')}")

    conds = [r.get("sql_condition") for r in rules]
    # Check that M101, M102, M105 are in the condition and NOT V3001
    assert any("M101" in c and "M102" in c and "M105" in c and "NOT IN" in c for c in conds), "Failed dynamic supplier code extraction"
    assert not any("V3001" in c for c in conds), "Hardcoded V3001 leaked into unseen policy!"
    assert any("type = 'Expedited'" in c for c in conds), "Failed dynamic category Expedited extraction"
    assert not any("Adjustment" in c for c in conds), "Hardcoded Adjustment leaked into unseen policy!"
    assert any("raw_amount > 350000" in c for c in conds), "Failed dynamic threshold > 350000 extraction"
    assert not any("1800000" in c for c in conds), "Hardcoded 1800000 leaked into unseen policy!"
    assert any("type = 'Regular'" in c and "raw_amount <= 350000" in c for c in conds), "Failed dynamic approval rule synthesis"

    print("✓ TEST 2 PASSED: Arbitrary unseen policy handled dynamically with ZERO hardcoded values!")

def test_database_evaluation():
    print("\n" + "=" * 60)
    print("TEST 3: Live PostgreSQL Evaluation with English Policy")
    print("=" * 60)
    doc_text = """Rule 1 — Vendor Registration
The following vendor codes are registered: V3001, V3002, V3004, V3005, V3006, V3007, V3008, V3009, V3010, V3011, and V3012.
Hold any voucher whose vendor code is not on this list.

Rule 2 — Adjustment Review
Hold every voucher with category Adjustment, regardless of amount or vendor. Manual finance review is mandatory.

Rule 3 — High-Value Review
Hold every voucher whose amount is strictly greater than ¥1,800,000. This rule applies to all vendors.
An amount equal to ¥1,800,000 does not trigger this rule.

Rule 4 — Routine Approval
Approve a voucher only if:
The vendor code is registered.
The category is Routine.
The amount is ¥1,800,000 or less.
No mandatory Hold rule applies."""

    res = copilot_engine.evaluate(process_type="invoice", document_text=doc_text, filename_or_title="Live Eval")
    decisions = res.get("staged_decisions", [])
    appr_cnt = res.get("approved_count", 0)
    hold_cnt = res.get("hold_count", 0)
    print(f"Total Evaluated: {len(decisions)} rows")
    print(f"Approved Count: {appr_cnt}")
    print(f"Hold Count:     {hold_cnt}")

    # Inspect reasons for hold rows
    holds = res.get("discrepancies", [])
    print(f"\nSample 5 Hold Vouchers:")
    for h in holds[:5]:
        print(f"  Voucher {h['id']} ({h['employee_id']} - {h['name']}): Amount={h['amount']}, Type={h['type']}")
        print(f"    Matched Rule: {h['matched_rule']} ({h['matched_rule_id']})")
        print(f"    Reasons: {h['reasons']}")

    assert len(decisions) == 105, f"Expected 105 rows, got {len(decisions)}"
    assert appr_cnt > 0 and hold_cnt > 0, "Evaluation failed to separate approved vs hold"
    print("\n✓ TEST 3 PASSED: Live database evaluation matched correctly against SQL conditions!")

if __name__ == "__main__":
    test_english_sample()
    test_arbitrary_unseen_policy()
    test_database_evaluation()
