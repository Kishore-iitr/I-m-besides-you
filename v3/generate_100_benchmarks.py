"""
Generator for 100+ Realistic Benchmarks for Invoice and Payroll ERP Tables
Covering Dataset A and Dataset B distributions, vendor contracts, employee claims, and edge cases.
"""

import json

def build_105_invoices():
    vendors = [
        ("V3005", "Global Tech LLC", 716232, "Routine", "月次定額保守費"),
        ("V3006", "Hokuriku Parts Industry Co., Ltd.", 455128, "Routine", "消耗部品定額保守費"),
        ("V3006", "Hokuriku Parts Industry Co., Ltd.", 452219, "Routine", "消耗部品定期交換費"),
        ("V3002", "Yamato Shoji Co., Ltd.", 1237439, "Routine", "事務管理外部委託費"),
        ("V3002", "Yamato Shoji Co., Ltd.", 1218687, "Routine", "事務管理定期保守費"),
        ("V3007", "Fukuoka System Design", 1832962, "Routine", "基幹システム運用保守費"),
        ("V3007", "Fukuoka System Design", 1993825, "Routine", "ネットワーク基盤保守費"),
        ("V3007", "Fukuoka System Design", 1685384, "Routine", "クラウドインフラ監視費"),
        ("V3001", "Yamada Manufacturing Co., Ltd.", 385000, "Routine", "月次金型定額保守費"),
        ("V3001", "Yamada Manufacturing Co., Ltd.", 374313, "Routine", "機械設備定期点検費"),
        ("V3009", "Tokyo Cloud Solutions", 890000, "Routine", "ERPクラウドホスティング費"),
        ("V3010", "Sendai Precision Tech", 620000, "Routine", "精密測定機器定額保守費"),
        ("V3011", "Sapporo Data Networks", 540000, "Routine", "拠点間専用線通信保守費"),
        ("V3012", "Hiroshima Advanced Engineering", 950000, "Routine", "自動化設備ライン保守費"),
    ]

    edge_cases = [
        # Okinawa Logistics Adjustment (Classic Dataset B benchmark)
        ("V3008", "Okinawa Logistics Center", 317664, "Adjustment", "倉庫利用料変動調整額 (要物流部門検収)"),
        ("V3008", "Okinawa Logistics Center", 485200, "Adjustment", "突発輸送チャーター料調整 (役員承認要)"),
        ("V3006", "Hokuriku Parts Industry Co., Ltd.", 437452, "Adjustment", "部品緊急空輸割増差額 (未契約項目)"),
        ("V3004", "Kansai Software Lab", 2450000, "Routine", "大規模DB移行支援費 (上限200万円超過・要稟議)"),
        ("V3099", "Unknown Vendor Corp", 320000, "Routine", "新規取引先 (取引先マスタ未登録)"),
        ("V3007", "Fukuoka System Design", 2150000, "Routine", "サーバー増設臨時保守費 (上限超過)"),
    ]

    invoices = []
    inv_num_base = 7344
    slip_idx = 1

    # First add the core 12 from Dataset B benchmarks
    core_12 = [
        ("V3005", "Global Tech LLC", 716232, "Routine"),
        ("V3006", "Hokuriku Parts Industry Co., Ltd.", 455128, "Routine"),
        ("V3002", "Yamato Shoji Co., Ltd.", 1237439, "Routine"),
        ("V3007", "Fukuoka System Design", 1832962, "Routine"),
        ("V3008", "Okinawa Logistics Center", 317664, "Adjustment"),
        ("V3006", "Hokuriku Parts Industry Co., Ltd.", 452219, "Routine"),
        ("V3007", "Fukuoka System Design", 1993825, "Routine"),
        ("V3002", "Yamato Shoji Co., Ltd.", 1218687, "Routine"),
        ("V3001", "Yamada Manufacturing Co., Ltd.", 385000, "Routine"),
        ("V3006", "Hokuriku Parts Industry Co., Ltd.", 437452, "Adjustment"),
        ("V3001", "Yamada Manufacturing Co., Ltd.", 374313, "Routine"),
        ("V3007", "Fukuoka System Design", 1685384, "Routine"),
    ]

    for vcode, vname, amt, vtype in core_12:
        invoices.append({
            "id": f"P6-07010448-{slip_idx:03d}",
            "employee_id": vcode,
            "name": vname,
            "invoice_no": f"INV-2026-{inv_num_base}",
            "amount": f"¥{amt:,}",
            "raw_amount": amt,
            "type": vtype,
            "status": "Unprocessed",
            "ref": f"Order Ref : INV-2026-{inv_num_base}",
            "comment": ""
        })
        slip_idx += 1
        inv_num_base += 1

    # Now generate up to 105 invoices
    v_cycle = 0
    e_cycle = 0
    while len(invoices) < 105:
        # Every 8th record, insert an edge case / adjustment
        if len(invoices) % 8 == 0 and e_cycle < len(edge_cases):
            vcode, vname, amt, vtype, _ = edge_cases[e_cycle % len(edge_cases)]
            e_cycle += 1
        else:
            vcode, vname, base_amt, vtype, _ = vendors[v_cycle % len(vendors)]
            # slight jitter or exact agreement fee
            amt = base_amt
            v_cycle += 1

        invoices.append({
            "id": f"P6-07010448-{slip_idx:03d}",
            "employee_id": vcode,
            "name": vname,
            "invoice_no": f"INV-2026-{inv_num_base}",
            "amount": f"¥{amt:,}",
            "raw_amount": amt,
            "type": vtype,
            "status": "Unprocessed",
            "ref": f"Order Ref : INV-2026-{inv_num_base}",
            "comment": ""
        })
        slip_idx += 1
        inv_num_base += 1

    return invoices

def build_105_payroll_items():
    employees = [
        ("EMP-001", "青木 拓也"),
        ("EMP-002", "菊池 理恵"),
        ("EMP-003", "坂本 裕二"),
        ("EMP-004", "石田 美奈"),
        ("EMP-005", "桐島 涼介"),
        ("EMP-006", "江口 さくら"),
        ("EMP-007", "島田 奈々"),
        ("EMP-008", "高橋 健太"),
        ("EMP-009", "中村 優子"),
        ("EMP-010", "小林 大輔"),
        ("EMP-011", "加藤 雅人"),
        ("EMP-012", "吉田 真由美"),
        ("EMP-013", "山口 翔太"),
        ("EMP-014", "松本 陽菜"),
        ("EMP-015", "井上 蓮"),
        ("EMP-016", "木村 綾乃"),
        ("EMP-017", "清水 拓海"),
        ("EMP-018", "山崎 菜々美"),
        ("EMP-019", "森田 悠斗"),
        ("EMP-020", "橋本 葵"),
    ]

    standard_items = [
        ("研修費", "Addition", 77224),
        ("消耗品費", "Addition", 55571),
        ("出張旅費", "Addition", 64200),
        ("交通費精算", "Addition", 14850),
        ("残業手当調整", "Addition", 38400),
        ("昇給", "Addition", 25000),
        ("扶養控除変更", "Deduction", 18000),
        ("役職手当新設", "Addition", 40000),
        ("役職手当廃止", "Deduction", 35000),
        ("消耗品費", "Addition", 42100),
        ("出張旅費", "Addition", 58300),
        ("交通費精算", "Addition", 12400),
        ("在宅勤務手当", "Addition", 15000),
        ("資格取得手当", "Addition", 30000),
        ("研修費", "Addition", 85000),
        ("残業手当調整", "Addition", 42600),
    ]

    edge_items = [
        # Entertainment exceeding 100k (Classic Dataset B benchmark)
        ("接待交際費", "Addition", 145000, "業務委託規程第7条上限(10万円)超過・役員特別決裁要"),
        ("接待交際費", "Addition", 128000, "取引先接待費上限超過 (12.8万円)・要稟議書添付"),
        ("出張旅費", "Addition", 162000, "海外出張手当未承認項目・役員承認要"),
        ("扶養控除変更", "Addition", 20000, "控除項目が加算(Addition)に誤分類・区分不整合"),
        ("研修費", "Addition", 180000, "海外研修費用規程限度額超過 (18万円)"),
        ("未登録手当", "Addition", 50000, "人事給与マスタ未定義の手当コード"),
    ]

    payroll = []
    voucher_idx = 1
    ref_idx = 8

    # Core 10 from Dataset B benchmarks
    core_10 = [
        ("EMP-001", "青木 拓也", "研修費", "Addition", 77224, "P1-07089771-008"),
        ("EMP-002", "菊池 理恵", "消耗品費", "Addition", 55571, "P1-07089771-009"),
        ("EMP-003", "坂本 裕二", "出張旅費", "Addition", 64200, "P1-07089771-010"),
        ("EMP-004", "石田 美奈", "交通費精算", "Addition", 14850, "P1-07089771-011"),
        ("EMP-005", "桐島 涼介", "残業手当調整", "Addition", 38400, "P4-07054374-012"),
        ("EMP-006", "江口 さくら", "昇給", "Addition", 25000, "P4-07054374-012"),
        ("EMP-007", "島田 奈々", "扶養控除変更", "Deduction", 18000, "P5-07054374-012"),
        ("EMP-001", "青木 拓也", "接待交際費", "Addition", 145000, "P1-07089771-012"),
        ("EMP-002", "菊池 理恵", "役職手当新設", "Addition", 40000, "P4-07054374-012"),
        ("EMP-003", "坂本 裕二", "役職手当廃止", "Deduction", 35000, "P4-07054374-012"),
    ]

    for empid, empname, cat, itype, amt, vref in core_10:
        payroll.append({
            "id": f"P4-07089771-{voucher_idx:03d}",
            "employee_id": empid,
            "employee_name": empname,
            "item_category": cat,
            "item_type": itype,
            "amount": f"¥{amt:,}",
            "raw_amount": amt,
            "status": "Unprocessed",
            "voucher_ref": vref,
            "comment": ""
        })
        voucher_idx += 1
        ref_idx += 1

    # Fill up to 105
    emp_i = 7
    std_i = 0
    edge_i = 0
    while len(payroll) < 105:
        empid, empname = employees[emp_i % len(employees)]
        emp_i += 1

        if len(payroll) % 9 == 0 and edge_i < len(edge_items):
            cat, itype, amt, _ = edge_items[edge_i % len(edge_items)]
            edge_i += 1
        else:
            cat, itype, amt = standard_items[std_i % len(standard_items)]
            std_i += 1

        ref_v = f"P1-07089771-{ref_idx:03d}" if ref_idx < 100 else f"P4-07054374-{ref_idx%50:03d}"
        ref_idx += 1

        payroll.append({
            "id": f"P4-07089771-{voucher_idx:03d}",
            "employee_id": empid,
            "employee_name": empname,
            "item_category": cat,
            "item_type": itype,
            "amount": f"¥{amt:,}",
            "raw_amount": amt,
            "status": "Unprocessed",
            "voucher_ref": ref_v,
            "comment": ""
        })
        voucher_idx += 1

    return payroll

if __name__ == '__main__':
    invs = build_105_invoices()
    pays = build_105_payroll_items()
    print(f"Generated {len(invs)} invoices and {len(pays)} payroll items.")
