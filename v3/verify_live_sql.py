import requests
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:5135"

# Test GET /
res_get = requests.get(BASE_URL + "/")
assert res_get.status_code == 200, f"GET / failed with status {res_get.status_code}"
assert "SQL Condition / Predicate" in res_get.text, "Header 'SQL Condition / Predicate' not in HTML!"
print("GET / verification passed: Header and UI updated.")

# User's test policy
doc_text = """月次定期サービス・外注業務委託照合基準 (2026年度 下半期 財務経理部門)
本規定は、ERPにおける月次受領請求書データに対する自動承認（Approved）および人間精査保留（Hold）の判定ルールを定める。

【自動承認基準 (Auto-Approved Rules)】

全体基本原則:

区分（Category）が "Routine" であり、かつ 請求金額が 1,500,000円 以下 の伝票を対象とする。

対象ベンダーおよび許容金額:

East Japan Logistics (V1001): 倉庫定期管理費 ¥640,000 (固定)

NexTech Solutions (V1002): SaaS運用費 ¥820,000 または ¥910,000 (契約範囲内)

東海精密ツール (V1003): 金型定期メンテ費 ¥430,000 (固定)

Kyoto Creative Studio (V1004): デザイン業務委託費 ¥350,000 または ¥380,000 (月次上限内)

日本サイバーセキュリティ (V1005): SOC常時監視費 ¥1,200,000 (固定)

【保留・要人間精査基準 (Hold / Review Rules)】

金額上限超過: 単一伝票の金額が 1,500,000円 超 の場合は、契約登録済みであっても全て取締役/部門長承認が必要なため Hold とする。

区分条件: 区分（Category）が "Adjustment" または "Spot" の伝票は、理由の如何を問わず全て経理精査のため Hold とする。

特定取引先・案件の例外保留:

東海精密ツール (V1003): 金額が ¥430,000 以外の請求（特注治具・緊急補修等）はすべて Hold。

NexTech Solutions (V1002): 追加ライセンス調整費（区分 Adjustment）はすべて Hold。

未登録ベンダー: 上記対象ベンダーリストに含まれない取引先コード（例: V1099等）はマスタ不整合として一律 Hold。"""

res_analyze = requests.post(BASE_URL + "/api/copilot/analyze", json={
    "process_type": "invoice",
    "document_text": doc_text,
    "filename_or_title": "月次定期サービス・外注業務委託照合基準.docx"
})
assert res_analyze.status_code == 200, f"Analyze failed: {res_analyze.text}"
data = res_analyze.json()
assert data.get("success") is True
rules = data.get("rules", [])
print(f"\nSuccessfully extracted {len(rules)} rules via /api/copilot/analyze:")
for i, r in enumerate(rules):
    sql = r.get("sql_condition") or r.get("condition")
    assert sql, f"Rule {i+1} has no SQL condition!"
    assert "==" not in sql, f"Rule {i+1} has invalid '==' syntax: {sql}"
    assert "&&" not in sql, f"Rule {i+1} has invalid '&&' syntax: {sql}"
    assert "¥" not in sql, f"Rule {i+1} has currency symbol inside SQL: {sql}"
    print(f"[{i+1}] {r.get('rule_id')} | {r.get('match_value')} | Action: {r.get('action_on_match')}\n     SQL Predicate: {sql}")

# Test evaluate
res_eval = requests.post(BASE_URL + "/api/copilot/evaluate", json={
    "process_type": "invoice",
    "document_text": doc_text,
    "filename_or_title": "月次定期サービス・外注業務委託照合基準.docx",
    "custom_rules": rules
})
assert res_eval.status_code == 200, f"Evaluate failed: {res_eval.text}"
eval_data = res_eval.json()
assert eval_data.get("success") is True
print(f"\nSuccessfully evaluated {eval_data.get('evaluated_count')} database rows via /api/copilot/evaluate.")
print("Approved:", eval_data.get("approved_count"), "| Hold:", eval_data.get("hold_count"))
print("\nALL VERIFICATIONS PASSED!")
