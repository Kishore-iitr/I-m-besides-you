import sys
sys.stdout.reconfigure(encoding="utf-8")
from copilot_langgraph_engine import CoPilotLangGraph
from test_api_analyze import user_prompt

test_records = [
    {"id": "T-V1001", "employee_id": "V1001", "name": "East Japan Logistics", "type": "Routine", "amount": "¥640,000", "raw_amount": 640000},
    {"id": "T-V1002-OK", "employee_id": "V1002", "name": "NexTech Solutions", "type": "Routine", "amount": "¥820,000", "raw_amount": 820000},
    {"id": "T-V1002-ADJ", "employee_id": "V1002", "name": "NexTech Solutions", "type": "Adjustment", "amount": "¥150,000", "raw_amount": 150000},
    {"id": "T-V1003-OK", "employee_id": "V1003", "name": "東海精密ツール", "type": "Routine", "amount": "¥430,000", "raw_amount": 430000},
    {"id": "T-V1003-NG", "employee_id": "V1003", "name": "東海精密ツール", "type": "Routine", "amount": "¥550,000", "raw_amount": 550000},
    {"id": "T-V1004-OK", "employee_id": "V1004", "name": "Kyoto Creative Studio", "type": "Routine", "amount": "¥350,000", "raw_amount": 350000},
    {"id": "T-V1005-OK", "employee_id": "V1005", "name": "日本サイバーセキュリティ", "type": "Routine", "amount": "¥1,200,000", "raw_amount": 1200000},
    {"id": "T-V1005-CEIL", "employee_id": "V1005", "name": "日本サイバーセキュリティ", "type": "Routine", "amount": "¥2,000,000", "raw_amount": 2000000},
    {"id": "T-V1099-UNREG", "employee_id": "V1099", "name": "Unregistered Vendor Corp", "type": "Routine", "amount": "¥300,000", "raw_amount": 300000},
]

c = CoPilotLangGraph()
# Parse prompt into 10 rules
p_out = c.analyze_policy("invoice", user_prompt, "user_policy.txt")
rules = p_out["rules"]
print(f"Extracted Rules Count: {len(rules)}")
for r in rules:
    print(f" - {r['rule_id']}: {r['name']} -> {r['action_on_match']} ({r.get('condition')})")

# Evaluate state with custom test records
initial_state = c._prepare_initial_state("invoice", user_prompt, "user_policy.txt")
initial_state["current_db_rows"] = test_records
initial_state["policy_json"] = p_out["policy_json"]

decisions_out = c.node_compare_and_decide(initial_state)
print("\n--- DECISIONS ON ALL TEST CASES ---")
all_passed = True
expected_results = {
    "T-V1001": ("Approved", "RULE-INV-01"),
    "T-V1002-OK": ("Approved", "RULE-INV-02"),
    "T-V1002-ADJ": ("Hold", "RULE-INV-07"),
    "T-V1003-OK": ("Approved", "RULE-INV-03"),
    "T-V1003-NG": ("Hold", "RULE-INV-08"),
    "T-V1004-OK": ("Approved", "RULE-INV-04"),
    "T-V1005-OK": ("Approved", "RULE-INV-05"),
    "T-V1005-CEIL": ("Hold", "RULE-INV-06"),
    "T-V1099-UNREG": ("Hold", "RULE-INV-10"),
}

for d in decisions_out["decisions"]:
    rid = d["id"]
    st = d["new_status"]
    rule = d["matched_rule_id"]
    exp_st, exp_rule = expected_results[rid]
    passed = (st == exp_st and (rule == exp_rule or rule.startswith(exp_rule[:10])))
    status_icon = "✓ PASS" if passed else "✗ FAIL"
    if not passed: all_passed = False
    print(f"[{status_icon}] {rid:<14} -> Status: {st:<9} (Expected: {exp_st:<9}) | Rule: {rule:<12} ({d['matched_rule_summary']})")
    print(f"       Audit Note: {d['comment']}\n")

print(f"ALL TEST CASES PASSED: {all_passed}")
