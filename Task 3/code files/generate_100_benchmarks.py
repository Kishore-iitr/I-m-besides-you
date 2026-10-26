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
            "vendor_code": vcode,
            "vendor_name": vname,
            "employee_id": vcode,
            "name": vname,
            "customer_name": vname,
            "invoice_no": f"INV-2026-{inv_num_base}",
            "amount": f"¥{amt:,}",
            "raw_amount": amt,
            "total_amount": amt,
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
            "vendor_code": vcode,
            "vendor_name": vname,
            "employee_id": vcode,
            "name": vname,
            "customer_name": vname,
            "invoice_no": f"INV-2026-{inv_num_base}",
            "amount": f"¥{amt:,}",
            "raw_amount": amt,
            "total_amount": amt,
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

def build_105_leave_applications():
    employees = [
        ("EMP-001", "青木 拓也", "開発部", 14.5),
        ("EMP-002", "菊池 理恵", "総務部", 12.0),
        ("EMP-003", "坂本 裕二", "営業部", 8.0),
        ("EMP-004", "石田 美奈", "経理部", 15.0),
        ("EMP-005", "桐島 涼介", "開発部", 5.0),
        ("EMP-006", "江口 さくら", "人事部", 18.0),
        ("EMP-007", "島田 奈々", "カスタマーサポート", 6.5),
        ("EMP-008", "高橋 健太", "営業部", 1.0),
        ("EMP-009", "中村 優子", "開発部", 10.0),
        ("EMP-010", "小林 大輔", "品質管理部", 3.0),
        ("EMP-011", "加藤 雅人", "営業部", 0.0),
        ("EMP-012", "吉田 真由美", "経理部", 11.5),
        ("EMP-013", "山口 翔太", "開発部", 2.0),
        ("EMP-014", "松本 陽菜", "人事部", 7.0),
        ("EMP-015", "井上 蓮", "営業部", 9.0),
        ("EMP-016", "木村 綾乃", "総務部", 16.0),
        ("EMP-017", "清水 拓海", "開発部", 4.0),
        ("EMP-018", "山崎 菜々美", "カスタマーサポート", 13.0),
        ("EMP-019", "森田 悠斗", "営業部", 8.5),
        ("EMP-020", "橋本 葵", "品質管理部", 12.0),
    ]

    standard_patterns = [
        ("有給休暇", 1.0, "私用のため", False, None),
        ("半日有給申請", 0.5, "通院（午前休）のため", False, None),
        ("有給休暇", 2.0, "私用および家庭都合のため", False, None),
        ("夏季特別休暇", 3.0, "夏季一斉取得期間に伴う休暇", False, None),
        ("慶弔特別休暇", 3.0, "親族結婚式参列のため", True, "結婚式案内状_提出済.pdf"),
        ("病気休暇", 2.0, "発熱・体調不良による療養", True, "医師診断書_202607.pdf"),
        ("有給休暇", 1.0, "私用のため", False, None),
        ("半日有給申請", 0.5, "役所手続き（午後休）のため", False, None),
        ("在宅研修休暇", 1.0, "専門技術資格オンライン研修受講", True, "研修受講計画書_承認済.pdf"),
        ("有給休暇", 2.0, "私用のため", False, None),
    ]

    edge_cases = [
        # Quota exceeded (requested > remaining_balance)
        ("EMP-011", "加藤 雅人", "営業部", 0.0, "有給休暇", 2.0, "私用（残日数0日・残数超過）", False, None),
        ("EMP-008", "高橋 健太", "営業部", 1.0, "有給休暇", 3.0, "私用（残日数1日に対し3日申請・残数超過）", False, None),
        ("EMP-013", "山口 翔太", "開発部", 2.0, "有給休暇", 4.0, "旅行（残日数2日に対し4日申請・残数超過）", False, None),
        # Long consecutive leave (>3 or >5 days -> requires Director approval)
        ("EMP-001", "青木 拓也", "開発部", 14.5, "有給休暇", 5.0, "長期私用リフレッシュ（5日連続・部長決裁要）", False, None),
        ("EMP-004", "石田 美奈", "経理部", 15.0, "有給休暇", 7.0, "海外渡航（7日連続・役員決裁要）", False, None),
        # Special / Sick leave with MISSING attachment (has_attachment = False)
        ("EMP-005", "桐島 涼介", "開発部", 5.0, "慶弔特別休暇", 3.0, "親族不幸（会葬礼状等証明書未添付・要提出）", False, None),
        ("EMP-007", "島田 奈々", "カスタマーサポート", 6.5, "病気休暇", 4.0, "入院療養（診断書未添付・要再提出）", False, None),
        # Unregistered leave type
        ("EMP-010", "小林 大輔", "品質管理部", 3.0, "未登録休暇", 1.0, "社外ボランティア活動（人事マスタ未定義休暇区分）", False, None),
    ]

    records = []
    
    # Core Dataset B reference cases
    records.append({
        "id": "LV-2026-001",
        "employee_id": "EMP-001",
        "employee_name": "青木 拓也",
        "department": "開発部",
        "leave_type": "半日有給申請",
        "start_date": "2026-07-10",
        "end_date": "2026-07-10",
        "requested_days": 0.5,
        "remaining_balance": 14.5,
        "reason": "通院のため（午後休）",
        "has_attachment": False,
        "attachment_name": None,
        "voucher_ref": "P2-07101496-012",
        "status": "Unprocessed",
        "comment": ""
    })
    records.append({
        "id": "LV-2026-002",
        "employee_id": "EMP-002",
        "employee_name": "菊池 理恵",
        "department": "総務部",
        "leave_type": "有給休暇",
        "start_date": "2026-07-14",
        "end_date": "2026-07-15",
        "requested_days": 2.0,
        "remaining_balance": 12.0,
        "reason": "私用のため",
        "has_attachment": False,
        "attachment_name": None,
        "voucher_ref": "P6-07101496-012",
        "status": "Unprocessed",
        "comment": ""
    })

    edge_idx = 3
    for ec in edge_cases:
        empid, empname, dept, rem_bal, ltype, req_days, reason, has_att, att_name = ec
        records.append({
            "id": f"LV-2026-{edge_idx:03d}",
            "employee_id": empid,
            "employee_name": empname,
            "department": dept,
            "leave_type": ltype,
            "start_date": "2026-07-20",
            "end_date": "2026-07-24",
            "requested_days": req_days,
            "remaining_balance": rem_bal,
            "reason": reason,
            "has_attachment": has_att,
            "attachment_name": att_name,
            "voucher_ref": f"P2-07101496-{edge_idx:03d}",
            "status": "Unprocessed",
            "comment": ""
        })
        edge_idx += 1

    curr_id = len(records) + 1
    pat_idx = 0
    emp_idx = 0

    while len(records) < 105:
        empid, empname, dept, default_bal = employees[emp_idx % len(employees)]
        ltype, req_days, r_reason, has_att, att_name = standard_patterns[pat_idx % len(standard_patterns)]
        day_start = 5 + (curr_id % 24)
        s_date = f"2026-07-{day_start:02d}"
        e_date = f"2026-07-{min(day_start + int(req_days), 28):02d}"

        records.append({
            "id": f"LV-2026-{curr_id:03d}",
            "employee_id": empid,
            "employee_name": empname,
            "department": dept,
            "leave_type": ltype,
            "start_date": s_date,
            "end_date": e_date,
            "requested_days": req_days,
            "remaining_balance": default_bal,
            "reason": r_reason,
            "has_attachment": has_att,
            "attachment_name": att_name,
            "voucher_ref": f"P2-07101496-{curr_id:03d}",
            "status": "Unprocessed",
            "comment": ""
        })
        curr_id += 1
        pat_idx += 1
        emp_idx += 1

    return records

generate_105_leave_applications = build_105_leave_applications

if __name__ == '__main__':
    invs = build_105_invoices()
    pays = build_105_payroll_items()
    leaves = build_105_leave_applications()
    print(f"Generated {len(invs)} invoices, {len(pays)} payroll items, and {len(leaves)} leave applications.")
