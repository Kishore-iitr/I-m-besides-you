import requests
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_URL = "http://127.0.0.1:5135"

def test_app():
    # 1. Check HTML
    res = requests.get(f"{BASE_URL}/")
    res.encoding = "utf-8"
    assert res.status_code == 200, f"Status code: {res.status_code}"
    html = res.text
    
    # Check title and header
    assert "基幹統合業務システム" in html, "Missing 基幹統合業務システム in HTML"
    assert "企業会計・人事給与 自動照合管理" in html, "Missing 企業会計・人事給与 自動照合管理 in HTML"
    assert "module-banner" not in html, "Found module-banner in HTML"
    assert "Dataset A" not in html, "Found Dataset A in HTML"
    assert "Dataset B" not in html, "Found Dataset B in HTML"
    assert "Excel Export" not in html, "Found Excel Export in HTML"
    assert "Excel一括取込" in html, "Missing Excel一括取込 in HTML"
    assert "🏛️ 財務会計" in html, "Missing 🏛️ 財務会計 tab in HTML"
    assert "👥 人事給与" in html, "Missing 👥 人事給与 tab in HTML"
    print("✓ HTML verification passed! Clutter, brackets, and banners removed. Clean tabs & Excel import present.")

    # 2. Check DB status
    res = requests.get(f"{BASE_URL}/api/database/status")
    assert res.status_code == 200
    db_stat = res.json()
    print("✓ DB Status:", db_stat)

    # 3. Check Invoices
    res = requests.get(f"{BASE_URL}/api/invoices")
    assert res.status_code == 200
    invoices = res.json()
    print(f"✓ Invoices returned: {len(invoices)} records")

    # 4. Check Payroll Items
    res = requests.get(f"{BASE_URL}/api/payroll-items")
    assert res.status_code == 200
    payroll_items = res.json()
    print(f"✓ Payroll Items returned: {len(payroll_items)} records")

    print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    try:
        test_app()
    except Exception as e:
        print("Verification failed:", e)
        sys.exit(1)
