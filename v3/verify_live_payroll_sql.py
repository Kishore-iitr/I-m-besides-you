import requests
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")
BASE_URL = "http://127.0.0.1:5135"

PAYROLL_MEMO = """【社内経費精算・旅費日当照合基準（2026年度版）】
1. 青木 拓也 (P4-07089771-001): 研修費 ¥77,224 (事前承認済技術研修)
2. 菊地 里江 (P4-07089771-002): 消耗品費 ¥42,800 (開発資材領収書添付済)
3. 坂本 裕二 (P4-07089771-003): 出張旅費 ¥89,500 (大阪支社技術支援出張)
【保留・人間精査基準】
- 接待交際費で 100,000円 超過 の伝票は要役員決裁のため一律 Hold。
- 控除項目（扶養控除変更、役職手当廃止等）で区分が「Addition（支給）」になっている伝票はマスタ不整合のため Hold。
- 1伝票の精算金額が 150,000円 超過 のものは事前稟議書添付が必要なため Hold。
- 就業規則別表に定められていない未登録手当（コード不明）は人事承認が必要なため Hold。"""

res_pay = requests.post(BASE_URL + "/api/copilot/analyze", json={
    "process_type": "payroll",
    "document_text": PAYROLL_MEMO,
    "filename_or_title": "精算確認メモ.txt"
})
assert res_pay.status_code == 200, f"Analyze payroll failed: {res_pay.text}"
data_pay = res_pay.json()
assert data_pay.get("success") is True
rules_pay = data_pay.get("rules", [])
print(f"\nSuccessfully extracted {len(rules_pay)} payroll rules via /api/copilot/analyze:")
for i, r in enumerate(rules_pay):
    sql = r.get("sql_condition") or r.get("condition")
    assert sql, f"Payroll Rule {i+1} has no SQL condition!"
    assert "==" not in sql, f"Payroll Rule {i+1} has invalid '==' syntax: {sql}"
    assert "&&" not in sql, f"Payroll Rule {i+1} has invalid '&&' syntax: {sql}"
    assert "¥" not in sql, f"Payroll Rule {i+1} has currency symbol inside SQL: {sql}"
    print(f"[{i+1}] {r.get('rule_id')} | {r.get('match_value')} | Action: {r.get('action_on_match')}\n     SQL Predicate: {sql}")

res_eval_pay = requests.post(BASE_URL + "/api/copilot/evaluate", json={
    "process_type": "payroll",
    "document_text": PAYROLL_MEMO,
    "filename_or_title": "精算確認メモ.txt",
    "custom_rules": rules_pay
})
assert res_eval_pay.status_code == 200, f"Evaluate payroll failed: {res_eval_pay.text}"
eval_data_pay = res_eval_pay.json()
assert eval_data_pay.get("success") is True
print(f"\nSuccessfully evaluated {eval_data_pay.get('evaluated_count')} payroll items via /api/copilot/evaluate.")
print("Confirmed:", eval_data_pay.get("approved_count"), "| Hold:", eval_data_pay.get("hold_count"))
print("\nALL PAYROLL VERIFICATIONS PASSED!")
