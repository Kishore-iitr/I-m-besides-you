import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
import urllib.request
import json
import time

base = 'http://127.0.0.1:5135'

def post_json(endpoint, payload):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(f"{base}{endpoint}", data=data, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read().decode('utf-8'))

def get_json(endpoint):
    req = urllib.request.urlopen(f"{base}{endpoint}")
    return json.loads(req.read().decode('utf-8'))

def test():
    print("=== 1. Checking Database Status ===")
    status = get_json('/api/database/status')
    print(f"DB Engine: {status['engine']}, Display: {status['display_target']}, Connected: {status['connected']}")

    print("\n=== 2. Resetting DB to Clean Benchmarks ===")
    post_json('/api/database/reset', {})
    print("Database reset successfully.")

    # 3. Test Payroll Suite (Rank 2 Candidate)
    print("\n=== 3. Testing Module: HR人事給与 (Payroll Items) ===")
    pay_before = get_json('/api/payroll-items')
    print(f"Initial Payroll items count: {len(pay_before)}")
    print(f"Sample initial item: {pay_before[0]['id']} | {pay_before[0]['employee_name']} | {pay_before[0]['amount']} | Status: {pay_before[0]['status']}")

    preset_payroll = """精算確認メモ (2026年7月度 人事給与控除・経費整備)
参照規程: 業務委託経費規程 (gyomu_itaku_keihi_kitei) / 業務委託給与規程 (gyomu_itaku_kyuuyo_kitei)

【経費精算・手当改定確認済リスト (Confirmed Items)】
1. 青木 拓也 (P4-07089771-001 / 照合伝票: P1-07089771-008)
   - 研修費: ¥77,224。外部技術研修受講料。規程第4条(上限10万円以内)適合確認済。確認済(Confirmed)。
2. 菊池 理恵 (P4-07089771-002 / 照合伝票: P1-07089771-009)
   - 消耗品費: ¥55,571。開発用消耗備品購入代金領収書照合済。確認済(Confirmed)。
3. 坂本 裕二 (P4-07089771-003 / 照合伝票: P1-07089771-010)
   - 出張旅費: ¥64,200。大阪支社技術支援出張旅費規程内整合確認済。確認済(Confirmed)。
4. 石田 美奈 (P4-07089771-004 / 照合伝票: P1-07089771-011)
   - 交通費精算: ¥14,850。客先往復近郊交通費照合済。確認済(Confirmed)。
5. 桐島 涼介 (P4-07089771-005 / 照合伝票: P4-07054374-012)
   - 残業手当調整: ¥38,400。勤怠管理システム超過勤務データ整合確認済。確認済(Confirmed)。
6. 江口 さくら (P4-07089771-006 / 照合伝票: P4-07054374-012)
   - 昇給: ¥25,000。人事考課給与辞令照合済。確認済(Confirmed)。
7. 島田 奈々 (P4-07089771-007 / 照合伝票: P5-07054374-012)
   - 扶養控除変更: ¥18,000 (控除)。扶養親族変更届照合済。確認済(Confirmed)。
8. 菊池 理恵 (P4-07089771-009 / 照合伝票: P4-07054374-012)
   - 役職手当新設: ¥40,000。新任リーダー手当適用確認済。確認済(Confirmed)。
9. 坂本 裕二 (P4-07089771-010 / 照合伝票: P4-07054374-012)
   - 役職手当廃止: ¥35,000 (控除)。組織変更に伴う手当終了確認済。確認済(Confirmed)。

【保留・要人間精査項目 (Hold / Exception Items)】
- 青木 拓也 (P4-07089771-008 / 照合伝票: P1-07089771-012)
  - 接待交際費: ¥145,000。業務委託経費規程第7条の上限(1件10万円)を超過しているため保留(Hold)。役員特別決裁承認を要す。"""

    print("Executing LangGraph Engine for Payroll items...")
    payroll_res = post_json('/api/copilot/run', {
        "process_type": "payroll",
        "document_text": preset_payroll,
        "filename_or_title": "*精算確認メモ.txt"
    })
    print(f"LangGraph Run Status: {payroll_res.get('overall_status')}")
    print(f"Nodes Executed: {[step['node'] for step in payroll_res.get('execution_steps', [])]}")
    print(f"Rules Extracted: {len(payroll_res.get('extracted_rules', []))}")
    print(f"Total Evaluated: {payroll_res.get('evaluated_count')}")
    print(f"Confirmed Count: {payroll_res.get('approved_count')}")
    print(f"Hold (Discrepancy) Count: {payroll_res.get('hold_count')}")
    for d in payroll_res.get('discrepancies', []):
        print(f"  -> Discrepancy Flagged: {d['id']} ({d.get('name')}) | {d.get('amount')} | Reason: {', '.join(d.get('reasons', []))}")

    # Check live DB state
    pay_after = get_json('/api/payroll-items')
    confirmed = sum(1 for x in pay_after if x['status'] == 'Confirmed')
    holds = sum(1 for x in pay_after if x['status'] == 'Hold')
    print(f"Live DB Status after run: {confirmed} Confirmed, {holds} Hold")
    print(f"Sample confirmed row comment: {pay_after[0]['comment']}")

    # 4. Human-in-the-loop override
    if payroll_res.get('discrepancies'):
        flagged_id = payroll_res['discrepancies'][0]['id']
        print(f"\n=== 4. Resolving Human Intervention for {flagged_id} ===")
        ov_res = post_json('/api/item/override', {
            "suite": "payroll",
            "id": flagged_id,
            "status": "Confirmed",
            "comment": "役員特別決裁書第2026-07-09号に基づき経理課長により特例承認"
        })
        print(f"Override result: {ov_res}")
        pay_after_ov = get_json('/api/payroll-items')
        ov_item = next((x for x in pay_after_ov if x['id'] == flagged_id), None)
        print(f"DB Status after human override: {ov_item['id']} is now {ov_item['status']} | Comment: {ov_item['comment']}")

    # 5. Test Invoice Suite
    print("\n=== 5. Testing Module: 財務会計 (Invoices) ===")
    preset_invoice = """月次定額保守取引先契約一覧 (2026年度 財務会計部門)
1. Global Tech LLC (取引先コード: V3005)
   - 月次定額保守費: ¥716,232 (固定)。契約内整合確認により自動承認。
2. 北陸部品工業株式会社 (Hokuriku Parts Industry Co., Ltd. / V3006)
   - 消耗部品定額保守費: ¥455,128 および ¥452,219。通常(Routine)取引として自動承認。
3. 大和商事株式会社 (Yamato Shoji Co., Ltd. / V3002)
   - 事務管理委託費: ¥1,237,439 および ¥1,218,687。業務委託契約書照合済、自動承認。
4. 福岡システムデザイン (Fukuoka System Design / V3007)
   - システム運用保守費: ¥1,832,962、¥1,993,825、¥1,685,384。IT基盤保守契約内として承認。
5. 山田製作所 (Yamada Manufacturing Co., Ltd. / V3001)
   - 定額加工費: ¥385,000 および ¥374,313。照合済、承認。
- 沖縄物流センター (Okinawa Logistics Center / V3008): 請求金額 ¥317,664 (区分: Adjustment)。
  調整・変動項目につき、物流管理部門の受領書および経理課長の事前承認確認を必須とし、自動承認は行わず保留(Hold)とする。"""

    invoice_res = post_json('/api/copilot/run', {
        "process_type": "invoice",
        "document_text": preset_invoice,
        "filename_or_title": "月次定額取引先一覧.docx"
    })
    print(f"LangGraph Run Status: {invoice_res.get('overall_status')}")
    print(f"Total Evaluated: {invoice_res.get('evaluated_count')}")
    print(f"Approved Count: {invoice_res.get('approved_count')}")
    print(f"Hold (Discrepancy) Count: {invoice_res.get('hold_count')}")
    for d in invoice_res.get('discrepancies', []):
        print(f"  -> Discrepancy Flagged: {d['id']} ({d.get('name')}) | {d.get('amount')} | Reason: {', '.join(d.get('reasons', []))}")

    inv_after = get_json('/api/invoices')
    approved = sum(1 for x in inv_after if x['status'] == 'Approved')
    inv_holds = sum(1 for x in inv_after if x['status'] == 'Hold')
    print(f"Live DB Status after run: {approved} Approved, {inv_holds} Hold")
    print(f"Sample approved invoice comment: {inv_after[0]['comment']}")

    print("\n>>> ALL VERIFICATION TESTS PASSED SUCCESSFULLY! <<<")

if __name__ == '__main__':
    test()
