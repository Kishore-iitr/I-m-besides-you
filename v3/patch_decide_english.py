with open('copilot_langgraph_engine.py', 'r', encoding='utf-8') as f:
    code = f.read()

old_block = '''            if process_type == "invoice":
                row_type = row.get("type", "Routine")
                is_adjustment = (row_type == "Adjustment") or (row.get("employee_id") == "V3008") or ("Adjustment" in str(row.get("ref", "")))
                is_ceiling = (amount > 2000000)

                if is_adjustment:
                    new_status = "Hold"
                    matched_rule_id = "RULE-INV-ADJ"
                    matched_rule_summary = "伝票区分「Adjustment」要経理精査"
                    reasons.append("伝票区分「Adjustment（調整取引）」につき物流管理受領書及び経理課長の事前承認が必要")
                elif is_ceiling:
                    new_status = "Hold"
                    matched_rule_id = "RULE-INV-CEILING"
                    matched_rule_summary = "自動承認限度額(200万円)超過"
                    reasons.append(f"請求金額 ¥{amount:,} が自動承認上限限度額（200万円）を超過。取締役経理担当の事前決裁が必要")
                elif matched_criterion:
                    if matched_criterion.get("action_on_match") == "Hold":
                        new_status = "Hold"
                        matched_rule_id = matched_criterion.get("rule_id", "RULE-INV-HOLD")
                        matched_rule_summary = matched_criterion.get("name", "契約例外個別保留")
                        reasons.append(matched_criterion.get("description", "個別例外規程により保留"))
                    else:
                        new_status = "Approved"
                        matched_rule_id = matched_criterion.get("rule_id", "RULE-INV-ROUTINE")
                        matched_rule_summary = matched_criterion.get("name", "月次定額保守契約整合")
                else:
                    new_status = "Approved"
                    matched_rule_id = "RULE-INV-GENERAL"
                    matched_rule_summary = "通常取引上限内承認"

                comment = self.llm_service.generate_comment(process_type, row, new_status, reasons)

            else:  # payroll
                cat = row.get("item_category", "")
                row_type = row.get("item_type", "Addition")

                # 1. First check if specific voucher was declared in memo
                if matched_criterion:
                    matched_rule_id = matched_criterion.get("rule_id", "RULE-PAY-VOUCHER")
                    matched_rule_summary = matched_criterion.get("name", "個別伝票精算照合")
                    if matched_criterion.get("action_on_match") == "Hold":
                        new_status = "Hold"
                        reasons.append(matched_criterion.get("description", "規定上限額超過につき役員事前承認要"))
                    else:
                        new_status = "Confirmed"
                # 2. General regulation compliance checks
                known_categories = ["交通費精算", "消耗品費", "出張旅費", "研修費", "在宅勤務手当", "残業手当調整", "接待交際費", "役職手当新設", "役職手当廃止", "扶養控除変更", "昇給", "資格取得手当"]
                is_unknown = (cat == "未登録手当") or (cat not in known_categories and not any(reg.get("name") == cat for reg in master_regs if "規程" in reg.get("code", "")))
                
                if is_unknown:
                    new_status = "Hold"
                    matched_rule_id = "RULE-PAY-UNKNOWN"
                    matched_rule_summary = "未定義手当コード"
                    reasons.append(f"「{cat}」は人事給与マスタ未定義の手当コードです。人事課長による手当新設承認を要します")
                elif (cat in ["扶養控除変更", "役職手当廃止"] or "控除" in cat) and row_type != "Deduction":
                    new_status = "Hold"
                    matched_rule_id = "RULE-PAY-CLASS"
                    matched_rule_summary = "控除項目の加算誤登録 (区分不整合)"
                    reasons.append(f"「{cat}」は控除項目(Deduction)である必要がありますが、加算(Addition)として誤登録されています")
                elif ("接待" in cat or "交際" in cat) and amount > 100000:
                    new_status = "Hold"
                    matched_rule_id = "RULE-PAY-ENT"
                    matched_rule_summary = "接待交際費上限10万円超過"
                    reasons.append(f"接待交際費（¥{amount:,}）が業務委託経費規程第7条の上限（10万円）を超過。役員特別決裁が必要です")
                elif amount > 150000:
                    new_status = "Hold"
                    matched_rule_id = "RULE-PAY-CEILING"
                    matched_rule_summary = "個別経費上限15万円超過"
                    reasons.append(f"申請金額（¥{amount:,}）が社内個別決済上限（15万円）を超過。事前稟議書の確認が必要です")
                else:
                    new_status = "Confirmed"
                    matched_rule_id = "RULE-PAY-STANDARD"
                    matched_rule_summary = "社内経費規程適合確認済"'''

new_block = '''            if process_type == "invoice":
                row_type = row.get("type", "Routine")
                is_adjustment = (row_type == "Adjustment") or (row.get("employee_id") == "V3008") or ("Adjustment" in str(row.get("ref", "")))
                is_ceiling = (amount > 2000000)

                if matched_criterion:
                    user_action = matched_criterion.get("action_on_match", "Approved")
                    matched_rule_id = matched_criterion.get("rule_id", "RULE-INV-CUSTOM")
                    matched_rule_summary = matched_criterion.get("description") or matched_criterion.get("name", "Custom Contract Rule")
                    if user_action in ("Hold", "Rejected"):
                        new_status = "Hold"
                        reasons.append(matched_criterion.get("description", "Held per policy condition"))
                    elif is_ceiling:
                        new_status = "Hold"
                        matched_rule_id = "RULE-INV-CEILING"
                        matched_rule_summary = "Billing amount exceeds ¥2,000,000 ceiling"
                        reasons.append(f"Billing amount ¥{amount:,} exceeds automatic approval ceiling (¥2,000,000). Executive sanction required.")
                    else:
                        new_status = "Approved"
                elif is_adjustment:
                    new_status = "Hold"
                    matched_rule_id = "RULE-INV-ADJ"
                    matched_rule_summary = "Voucher classification is 'Adjustment'"
                    reasons.append("Voucher classification is 'Adjustment' (non-standard transaction). Logistics inspection receipt and manager approval required.")
                elif is_ceiling:
                    new_status = "Hold"
                    matched_rule_id = "RULE-INV-CEILING"
                    matched_rule_summary = "Billing amount exceeds ¥2,000,000 ceiling"
                    reasons.append(f"Billing amount ¥{amount:,} exceeds automatic approval ceiling (¥2,000,000). Executive board director sanction required.")
                else:
                    new_status = "Approved"
                    matched_rule_id = "RULE-INV-ROUTINE"
                    matched_rule_summary = "Standard Routine Transaction"

                comment = self.llm_service.generate_comment(process_type, row, new_status, reasons)

            else:  # payroll
                cat = row.get("item_category", "")
                row_type = row.get("item_type", "Addition")

                # 1. First check if specific voucher or employee was declared in user rules
                if matched_criterion:
                    user_action = matched_criterion.get("action_on_match", "Confirmed")
                    matched_rule_id = matched_criterion.get("rule_id", "RULE-PAY-CUSTOM")
                    matched_rule_summary = matched_criterion.get("description") or matched_criterion.get("name", "Custom Payroll Policy Rule")
                    if user_action in ("Hold", "Rejected"):
                        new_status = "Hold"
                        reasons.append(matched_criterion.get("description", "Held per custom payroll policy condition"))
                    else:
                        new_status = "Confirmed"
                else:
                    # 2. General regulation compliance checks in English
                    known_categories = ["交通費精算", "消耗品費", "出張旅費", "研修費", "在宅勤務手当", "残業手当調整", "接待交際費", "役職手当新設", "役職手当廃止", "扶養控除変更", "昇給", "資格取得手当"]
                    is_unknown = (cat == "未登録手当") or (cat not in known_categories and not any(reg.get("name") == cat for reg in master_regs if "規程" in reg.get("code", "")))
                    
                    if is_unknown:
                        new_status = "Hold"
                        matched_rule_id = "RULE-PAY-UNKNOWN"
                        matched_rule_summary = "Undefined Allowance Code"
                        reasons.append(f"Allowance code/item '{cat}' is not defined in the HR payroll master. Requires HR department authorization.")
                    elif (cat in ["扶養控除変更", "役職手当廃止"] or "控除" in cat) and row_type != "Deduction":
                        new_status = "Hold"
                        matched_rule_id = "RULE-PAY-CLASS"
                        matched_rule_summary = "Classification Mismatch (Deduction registered as Addition)"
                        reasons.append(f"Item '{cat}' must be a Deduction, but is erroneously registered as Addition.")
                    elif ("接待" in cat or "交際" in cat) and amount > 100000:
                        new_status = "Hold"
                        matched_rule_id = "RULE-PAY-ENT"
                        matched_rule_summary = "Entertainment Expense Exceeds ¥100,000 Limit"
                        reasons.append(f"Entertainment expense (¥{amount:,}) exceeds Article 7 policy limit of ¥100,000. Executive special sanction required.")
                    elif amount > 150000:
                        new_status = "Hold"
                        matched_rule_id = "RULE-PAY-CEILING"
                        matched_rule_summary = "Single Expense Exceeds ¥150,000 Limit"
                        reasons.append(f"Expense amount (¥{amount:,}) exceeds standard single reimbursement ceiling of ¥150,000. Prior approval memo required.")
                    else:
                        new_status = "Confirmed"
                        matched_rule_id = "RULE-PAY-STANDARD"
                        matched_rule_summary = "Compliant with Corporate Expense Policy"'''

if old_block in code:
    code = code.replace(old_block, new_block)
    with open('copilot_langgraph_engine.py', 'w', encoding='utf-8') as f:
        f.write(code)
    print("Patched compare_and_decide with English reasons and custom rules support!")
else:
    print("Error: old_block not found in copilot_langgraph_engine.py")
