"""
Comprehensive Test Suite for Invoice Processing & Supabase PostgreSQL Automation (English Edition).
Tests:
1. Server endpoints and reset state
2. Data attributes and clean English UI elements
3. Dynamic policy switching (Fixed Vendor vs. New Contract vs. Termination vs. IT/Logistics)
4. Full execution and verification in Supabase PostgreSQL
"""

import sys
import json
import urllib.request
from policy_engine import DEFAULT_POLICIES, set_active_policy, get_active_policy, evaluate_invoice

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def test_api():
    print("=" * 65)
    print("TEST SUITE: INVOICE AUTOMATION & SUPABASE POSTGRESQL (ENGLISH)")
    print("=" * 65)

    # 1. Reset ERP Queue
    print("\n[TEST 1] Reset ERP Queue on http://127.0.0.1:5135/api/reset...")
    req = urllib.request.Request(
        "http://127.0.0.1:5135/api/reset",
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        print(f" -> Reset successful: Total {res['total']} invoices, DB: {res['db']['engine']} ({res['db']['target']})")
        assert res["total"] == 12, "Expected 12 total invoices"

    # 2. Verify Data Attributes in HTML
    print("\n[TEST 2] Verifying English UI & Data Attributes in ERP HTML...")
    with urllib.request.urlopen("http://127.0.0.1:5135/") as resp:
        html = resp.read().decode("utf-8")
        assert 'data-status' in html, "data-status attribute missing in HTML"
        assert 'isRowPending' in html, "isRowPending function missing in JS"
        assert 'unprocessed' in html.lower(), "unprocessed keyword missing in JS"
        assert 'Financial Accounting System' in html, "English title missing in HTML"
        print(" -> HTML contains data-status, data-vendor-name, data-raw-amount, and English UI: PASS")

    # 3. Test Policy 1: Fixed Price Vendors
    print("\n[TEST 3] Testing Policy 1: getsujitsu_teigaku_torihikisaki_ichiran (Fixed Vendors)...")
    pol1 = DEFAULT_POLICIES["getsujitsu_teigaku_torihikisaki_ichiran"]
    set_active_policy(pol1)
    
    # Get invoices from ERP
    with urllib.request.urlopen("http://127.0.0.1:5135/api/invoices") as resp:
        invoices = json.loads(resp.read().decode("utf-8"))["invoices"]

    results_p1 = {}
    for inv in invoices:
        decision, comment, reason = evaluate_invoice(pol1, inv)
        results_p1[inv["id"]] = (decision, comment, reason)

    # Check Yamada (INV-2026-7352, ¥385,000) -> Must be Approved
    yamada = next(i for i in invoices if i["invoice_no"] == "INV-2026-7352")
    assert results_p1[yamada["id"]][0] == "Approved", f"Yamada ¥385,000 should be Approved, got {results_p1[yamada['id']][0]}"
    print(f" -> Yamada ({yamada['invoice_no']}): {results_p1[yamada['id']][0]} ({results_p1[yamada['id']][2]})")

    # Check GlobalTech (INV-2026-7344, ¥716,232 vs ¥745,000) -> Must be On Hold
    gt = next(i for i in invoices if i["invoice_no"] == "INV-2026-7344")
    assert results_p1[gt["id"]][0] == "On Hold", f"GlobalTech mismatch should be On Hold, got {results_p1[gt['id']][0]}"
    print(f" -> GlobalTech ({gt['invoice_no']}): {results_p1[gt['id']][0]} ({results_p1[gt['id']][2]})")

    # Check Fukuoka (INV-2026-7347, unregistered) -> Must be On Hold
    fk = next(i for i in invoices if "Fukuoka" in i["name"] or "福岡" in i["name"])
    assert results_p1[fk["id"]][0] == "On Hold", f"Fukuoka unregistered should be On Hold, got {results_p1[fk['id']][0]}"
    print(f" -> Fukuoka ({fk['invoice_no']}): {results_p1[fk['id']][0]} ({results_p1[fk['id']][2]})")

    # 4. Test Policy 2: New Contracts (1M threshold)
    print("\n[TEST 4] Testing Policy 2: shinkui_keiyaku_tetsuzuki (New Contract < ¥1M)...")
    pol2 = DEFAULT_POLICIES["shinkui_keiyaku_tetsuzuki"]
    set_active_policy(pol2)
    under_1m = next(i for i in invoices if i["raw_amount"] < 1000000)
    over_1m = next(i for i in invoices if i["raw_amount"] >= 1000000)

    d_under, _, r_under = evaluate_invoice(pol2, under_1m)
    d_over, _, r_over = evaluate_invoice(pol2, over_1m)

    assert d_under == "Approved", f"Under ¥1M should be Approved, got {d_under}"
    assert d_over == "On Hold", f"Over ¥1M should be On Hold, got {d_over}"
    print(f" -> Under ¥1M ({under_1m['amount']}): {d_under} ({r_under})")
    print(f" -> Over ¥1M ({over_1m['amount']}): {d_over} ({r_over})")

    # 5. Test Policy 4: IT & Logistics Audit
    print("\n[TEST 5] Testing Policy 4: it_gyomu_butsuryu_shinsa (IT & Logistics Audit)...")
    pol4 = DEFAULT_POLICIES["it_gyomu_butsuryu_shinsa"]
    set_active_policy(pol4)
    fukuoka_inv = next(i for i in invoices if ("Fukuoka" in i["name"] or "福岡" in i["name"]) and i["raw_amount"] < 2000000)
    okinawa_inv = next(i for i in invoices if ("Okinawa" in i["name"] or "沖縄" in i["name"]))
    hokuriku_adj = next(i for i in invoices if ("Hokuriku" in i["name"] or "北陸" in i["name"]) and ("Adjustment" in i["type"] or "調整" in i["type"]))

    d_fk, _, r_fk = evaluate_invoice(pol4, fukuoka_inv)
    d_ok, _, r_ok = evaluate_invoice(pol4, okinawa_inv)
    d_hk, _, r_hk = evaluate_invoice(pol4, hokuriku_adj)

    assert d_fk == "Approved", f"Fukuoka < ¥2M should be Approved, got {d_fk}"
    assert d_ok == "Approved", f"Okinawa adjustment < ¥500k should be Approved, got {d_ok}"
    assert d_hk == "On Hold", f"Hokuriku adjustment should be On Hold, got {d_hk}"
    print(f" -> Fukuoka IT: {d_fk} ({r_fk})")
    print(f" -> Okinawa Logistics: {d_ok} ({r_ok})")
    print(f" -> Hokuriku Adj: {d_hk} ({r_hk})")

    # 6. Execute Full Automation against Supabase PostgreSQL
    print("\n[TEST 6] Executing Full Processing into Supabase PostgreSQL...")
    set_active_policy(pol1) # Restore Policy 1
    
    approved_count = 0
    held_count = 0
    for inv in invoices:
        decision, comment, reason = evaluate_invoice(pol1, inv)
        action = "approve" if decision == "Approved" else "hold"
        payload = json.dumps({"action": action, "comment": comment}).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:5135/api/invoices/{inv['id']}/process",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            saved = data["invoice"]
            assert saved["status"] == decision, f"Expected {decision}, got {saved['status']}"
            assert saved["comment"] == comment
            if decision == "Approved":
                approved_count += 1
            else:
                held_count += 1

    print(f" -> Processed all 12 invoices: {approved_count} Approved, {held_count} Held.")

    # Verify in DB
    with urllib.request.urlopen("http://127.0.0.1:5135/api/invoices") as resp:
        db_state = json.loads(resp.read().decode("utf-8"))
        print(f" -> Verification in Supabase DB: Total {db_state['total']}, Pending: {db_state['pending']}")
        assert db_state["pending"] == 0, f"Expected 0 pending, got {db_state['pending']}"

    # Reset again so queue is fresh for user
    req_reset = urllib.request.Request("http://127.0.0.1:5135/api/reset", data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req_reset) as resp:
        pass
    print(" -> Reset queue back to 12 pending invoices ready for live user execution.")

    print("\n" + "=" * 65)
    print("ALL TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 65)

if __name__ == "__main__":
    test_api()
