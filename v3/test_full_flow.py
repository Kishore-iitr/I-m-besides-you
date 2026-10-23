"""
Automated Test for End-to-End LLM SQL Policy Compilation, PostgreSQL Evaluation,
Human Intervention Override, and One-Time Token Dispatch.
"""

import sys
import json
import urllib.request

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def run_tests():
    print("=" * 65)
    print("END-TO-END TEST: LLM SQL COMPILER & HUMAN INTERVENTION")
    print("=" * 65)

    # 1. Reset Queue
    print("\n[STEP 1] Reset ERP queue to 12 pending invoices...")
    req = urllib.request.Request("http://127.0.0.1:5135/api/reset", data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        print(f" -> Queue reset: Total {res['total']} invoices in {res['db']['engine']}.")
        assert res["total"] == 12

    # 2. Compile Preset Policy via Portal
    print("\n[STEP 2] Fetching & compiling policy via Portal (http://127.0.0.1:5136/api/preset)...")
    with urllib.request.urlopen("http://127.0.0.1:5136/api/preset?key=getsujitsu_teigaku_torihikisaki_ichiran") as resp:
        policy_res = json.loads(resp.read().decode("utf-8"))
        print(f" -> Policy compiled: '{policy_res['policy_title']}'")
        print(f" -> Generated SQL Rules count: {len(policy_res.get('generated_sql_rules', []))}")
        print(f" -> Approved count: {policy_res['approved_count']}, Held: {policy_res['held_count']}, Discrepancies: {policy_res['discrepancy_count']}")
        assert len(policy_res.get("generated_sql_rules", [])) > 0
        assert policy_res["discrepancy_count"] > 0, "Expected discrepancies for human review"

    # 3. Verify Generated JSON File endpoint
    print("\n[STEP 3] Verifying generated SQL JSON endpoint (http://127.0.0.1:5136/api/policy/generated_json)...")
    with urllib.request.urlopen("http://127.0.0.1:5136/api/policy/generated_json") as resp:
        json_file = json.loads(resp.read().decode("utf-8"))
        assert "rules" in json_file, "Missing 'rules' in generated JSON file"
        print(" -> Valid JSON file served with SQL queries: PASS")
        for r in json_file["rules"]:
            print(f"    * Rule: {r.get('rule_name', r.get('rule_id'))} -> {r.get('target_action')} | SQL: {r.get('sql_query')[:60]}...")

    # 4. Human Intervention Override
    print("\n[STEP 4] Executing Human Intervention on Global Tech LLC (P6-07010448-001)...")
    override_payload = json.dumps({
        "invoice_id": "P6-07010448-001",
        "action": "hold",
        "comment": "Human Auditor confirmed: Contract rate variance of ¥28,768 detected. On hold for vendor clarification."
    }).encode("utf-8")
    req_override = urllib.request.Request(
        "http://127.0.0.1:5136/api/human_override",
        data=override_payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req_override) as resp:
        updated_state = json.loads(resp.read().decode("utf-8"))
        print(f" -> Human intervention recorded. Discrepancies remaining: {updated_state['discrepancy_count']}")
        item = updated_state["evaluated_invoices"]["P6-07010448-001"]
        assert item["human_override"] is True
        print(f" -> Overridden decision: {item['decision']} | Comment: {item['comment']}")

    # 5. One-Time Token Generation & Single-Use Enforcement
    print("\n[STEP 5] Testing One-Time Dispatch Token to prevent auto-start on refresh...")
    req_token = urllib.request.Request(
        "http://127.0.0.1:5136/api/dispatch_token",
        data=json.dumps({"policy_id": "getsujitsu_teigaku_torihikisaki_ichiran"}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req_token) as resp:
        token_data = json.loads(resp.read().decode("utf-8"))
        token = token_data["token"]
        url = token_data["url"]
        print(f" -> Token generated: {token}")
        print(f" -> Dispatch URL: {url}")

    # First verification should SUCCEED and consume the token
    print(" -> First claim of token by ERP tab...")
    with urllib.request.urlopen(f"http://127.0.0.1:5135/api/automation/verify_token?token={token}") as resp:
        res1 = json.loads(resp.read().decode("utf-8"))
        print(f"    Claim 1 result: valid={res1['valid']} (Token successfully consumed)")
        assert res1["valid"] is True

    # Second claim (simulating page refresh F5) MUST FAIL!
    print(" -> Second claim of token by ERP tab (simulating user pressing F5 / Refresh)...")
    try:
        req_second = urllib.request.Request(f"http://127.0.0.1:5135/api/automation/verify_token?token={token}")
        with urllib.request.urlopen(req_second) as resp:
            res2 = json.loads(resp.read().decode("utf-8"))
            assert False, "Token should not be valid twice!"
    except urllib.error.HTTPError as e:
        print(f"    Claim 2 result: HTTP {e.code} (Correctly rejected! Automation will NOT restart on refresh!)")
        assert e.code == 400

    print("\n" + "=" * 65)
    print("ALL TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
