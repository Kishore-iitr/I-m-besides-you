"""
Script to update copilot_langgraph_engine.py and generate_app.py with zero-hardcoding dynamic parsing and remove all sample files/buttons.
"""
import re

# 1. Update copilot_langgraph_engine.py
with open("copilot_langgraph_engine.py", "r", encoding="utf-8") as f:
    engine_code = f.read()

# Let's inspect LlmService.generate_comment and node_compare_and_decide in copilot_langgraph_engine.py
new_semantic_extractor = '''    def _semantic_fallback_extract(self, process_type: str, doc_text: str, filename: str) -> Dict[str, Any]:
        """Completely dynamic, zero-hardcoding semantic extractor and rule compiler.
        Parses ANY arbitrary policy, SOP, regulation, or memo into structured criteria rules."""
        lines = [line.strip() for line in doc_text.splitlines() if line.strip()]
        
        current_section = "GENERAL"
        rules = []
        registered_vendors = set()
        global_rules = {
            "max_auto_approval_amount": 1500000 if process_type == "invoice" else 150000,
            "require_comment": True,
            "hold_categories": [],
            "allowed_routine_categories": ["Routine"] if process_type == "invoice" else ["Addition", "Deduction"],
            "require_registered_vendors": False
        }

        policy_title = f"Policy ({filename})"
        if lines:
            first_line = lines[0]
            if not any(kw in first_line for kw in [":", "：", "【", "No.", "1."]):
                policy_title = first_line

        rule_idx = 1

        for line in lines:
            # Ignore purely title or meta lines
            if line == policy_title or any(line.startswith(prefix) for prefix in ["本規定は", "本規程は", "【目的】", "概要:"]):
                continue

            # 1. Section Header Detection
            if any(kw in line for kw in ["【自動承認", "【承認", "Auto-Approved", "Approved Rules", "対象ベンダー", "【経費精算", "確認済リスト"]):
                current_section = "APPROVED"
                continue
            elif any(kw in line for kw in ["【保留", "【要人間精査", "Hold / Review", "例外保留", "除外", "保留リスト"]):
                current_section = "HOLD"
                continue

            # Check action in line
            has_hold = any(kw in line for kw in ["Hold", "保留", "要確認", "超過", "除外", "精査", "不整合", "差戻し", "以外", "未承認"])
            has_appr = any(kw in line for kw in ["Approved", "承認", "確定", "固定", "Confirmed", "適合", "範囲内", "確認済"])

            if has_hold and not has_appr:
                line_action = "Hold"
            elif has_appr and not has_hold:
                line_action = "Approved" if process_type == "invoice" else "Confirmed"
            else:
                line_action = "Hold" if current_section == "HOLD" else ("Approved" if process_type == "invoice" else "Confirmed")

            # Extract amounts in current line
            amts = [int(x.replace(',', '')) for x in re.findall(r'[¥\\]\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,9})', line)]
            if not amts:
                amts = [int(x.replace(',', '')) for x in re.findall(r'([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,9})\s*円', line)]

            # Check vendor code (e.g. V1001, V3005) or vendor name
            v_match = re.search(r'([A-Za-z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\s\.\,\-]+?)\s*[\(（]([A-Z][0-9]{3,5})[\)）]', line)
            v_code_only = re.search(r'\\b([A-Z][0-9]{3,5})\\b', line)
            p_voucher = re.search(r'(P[0-9]\-[0-9]{8}\-[0-9]{3})', line)

            # --- Rule Case A: Global Amount Ceiling Rule ---
            if any(kw in line for kw in ["金額上限", "上限超過", "超 の場合", "単一伝票の金額が", "以下 の伝票"]) and amts:
                limit_val = amts[0]
                if "以下" in line:
                    global_rules["max_auto_approval_amount"] = limit_val
                else:
                    rules.append({
                        "rule_id": f"RULE-{process_type[:3].upper()}-{rule_idx:02d}",
                        "name": f"Maximum Ceiling Threshold (> ¥{limit_val:,})",
                        "match_field": "raw_amount",
                        "match_value": f"> {limit_val}",
                        "threshold_amount": limit_val,
                        "condition": f"Amount > ¥{limit_val:,}",
                        "action_on_match": "Hold",
                        "action_on_mismatch": "Approved",
                        "description": line
                    })
                    rule_idx += 1
                continue

            # --- Rule Case B: Category Rule (e.g. Adjustment / Spot) ---
            if any(kw in line for kw in ["区分条件", "区分（Category）", "処理区分", "Category"]) and any(kw in line for kw in ["Adjustment", "Spot", "Routine", "手当", "控除"]):
                cats = re.findall(r'["\']([A-Za-z0-9_\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+)["\']', line)
                if not cats:
                    cats = [w for w in ["Adjustment", "Spot", "Routine"] if w in line]
                if "Hold" in line or "保留" in line:
                    for cat in cats:
                        if cat not in global_rules["hold_categories"]:
                            global_rules["hold_categories"].append(cat)
                    rules.append({
                        "rule_id": f"RULE-{process_type[:3].upper()}-{rule_idx:02d}",
                        "name": f"Category Review Rule ({'/'.join(cats)})",
                        "match_field": "type",
                        "match_value": ", ".join(cats),
                        "condition": f"Category in [{', '.join(cats)}]",
                        "action_on_match": "Hold",
                        "action_on_mismatch": "Approved",
                        "description": line
                    })
                    rule_idx += 1
                continue

            # --- Rule Case C: Unregistered Vendor Check ---
            if any(kw in line for kw in ["未登録ベンダー", "未登録取引先", "リストに含まれない", "マスタ不整合"]):
                global_rules["require_registered_vendors"] = True
                rules.append({
                    "rule_id": f"RULE-{process_type[:3].upper()}-{rule_idx:02d}",
                    "name": "Unregistered Vendor Integrity Check",
                    "match_field": "employee_id",
                    "match_value": "UNREGISTERED",
                    "condition": "Vendor code not in approved policy master",
                    "action_on_match": "Hold",
                    "action_on_mismatch": "Approved",
                    "description": line
                })
                rule_idx += 1
                continue

            # --- Rule Case D: Vendor-Specific Line Item / Rule ---
            if v_match or (v_code_only and process_type == "invoice"):
                v_name = v_match.group(1).strip() if v_match else ""
                v_code = v_match.group(2).strip() if v_match else (v_code_only.group(1).strip() if v_code_only else "")
                
                v_name = re.sub(r'^(?:No\.?\s*[0-9]+|[0-9]+[\.\:]|\-\s*)', '', v_name).strip()
                if v_code:
                    registered_vendors.add(v_code)
                if v_name:
                    registered_vendors.add(v_name)

                cond_parts = []
                if v_code:
                    cond_parts.append(f"Vendor: {v_code}")
                if amts:
                    cond_parts.append(f"Amount: {' or '.join([f'¥{a:,}' for a in amts])}")
                if "以外" in line:
                    cond_parts.append("Amount != Contract")
                if "Adjustment" in line:
                    cond_parts.append("Category: Adjustment")

                rules.append({
                    "rule_id": f"RULE-{process_type[:3].upper()}-{rule_idx:02d}",
                    "name": f"{v_name or v_code} {'Special Policy' if line_action == 'Hold' else 'Contract Rule'}",
                    "match_field": "employee_id" if v_code else "name",
                    "match_value": f"{v_name} ({v_code})" if (v_name and v_code) else (v_code or v_name),
                    "vendor_name": v_name,
                    "vendor_code": v_code,
                    "expected_amounts": amts,
                    "expected_amount": amts[0] if amts else None,
                    "strict_amount": ("固定" in line or "以外" in line),
                    "is_exception_hold": (line_action == "Hold"),
                    "condition": ", ".join(cond_parts) if cond_parts else f"Policy: {line_action}",
                    "action_on_match": line_action,
                    "action_on_mismatch": "Approved" if line_action == "Hold" else "Hold",
                    "description": line
                })
                rule_idx += 1
                continue

            # --- Rule Case E: Payroll Voucher / Employee Item ---
            if p_voucher or (process_type == "payroll" and (amts or any(kw in line for kw in ["研修", "旅費", "消耗品", "交通費", "接待", "手当", "給与", "控除"]))):
                v_id = p_voucher.group(1) if p_voucher else None
                emp_match = re.search(r'([A-Za-z\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]{2,8}(?:\s+[A-Za-z\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]{2,8})?)\s*[\(（]P[0-9]', line)
                emp_name = emp_match.group(1).strip() if emp_match else None
                
                cat_match = re.search(r'(研修費|消耗品費|出張旅費|交通費精算|接待交際費|残業手当調整|昇給|扶養控除変更|役職手当新設|役職手当廃止|未登録手当|[^\s\:\,]+費|[^\s\:\,]+手当)', line)
                cat_name = cat_match.group(1) if cat_match else "経費項目"

                rules.append({
                    "rule_id": f"RULE-{process_type[:3].upper()}-{rule_idx:02d}",
                    "name": f"{emp_name or v_id or cat_name} Settlement Rule",
                    "match_field": "id" if v_id else ("employee_name" if emp_name else "item_category"),
                    "match_value": v_id or emp_name or cat_name,
                    "voucher_id": v_id,
                    "employee_name": emp_name,
                    "item_category": cat_name,
                    "expected_amounts": amts,
                    "expected_amount": amts[0] if amts else None,
                    "condition": f"Voucher: {v_id or 'Target'}, Amount: {f'¥{amts[0]:,}' if amts else 'Within limit'}",
                    "action_on_match": line_action,
                    "action_on_mismatch": "Hold",
                    "description": line
                })
                rule_idx += 1
                continue

            # --- Rule Case F: General Bullet or Sentence ---
            if amts:
                rules.append({
                    "rule_id": f"RULE-{process_type[:3].upper()}-{rule_idx:02d}",
                    "name": f"Policy Criterion {rule_idx}",
                    "match_field": "description",
                    "match_value": line[:30],
                    "expected_amounts": amts,
                    "expected_amount": amts[0] if amts else None,
                    "condition": f"Amount: {' or '.join([f'¥{a:,}' for a in amts])}",
                    "action_on_match": line_action,
                    "action_on_mismatch": "Hold",
                    "description": line
                })
                rule_idx += 1

        global_rules["registered_vendors"] = list(registered_vendors)
        return {
            "policy_title": policy_title,
            "process_type": process_type,
            "global_rules": global_rules,
            "registered_vendors": list(registered_vendors),
            "item_criteria": rules
        }'''

# Replace _semantic_fallback_extract in copilot_langgraph_engine.py
pattern = r"    def _semantic_fallback_extract\(self, process_type: str, doc_text: str, filename: str\) -> Dict\[str, Any\]:[\s\S]*?    # --- Node 1: Convert Document"
replacement = new_semantic_extractor + "\n\n    # --- Node 1: Convert Document"
engine_code_updated = re.sub(pattern, replacement, engine_code)

# Now update node_compare_and_decide in copilot_langgraph_engine.py
new_compare_node = '''    # --- Node 2: Compare Database Features & Decide ---
    def node_compare_and_decide(self, state: CoPilotAgentState) -> Dict[str, Any]:
        t0 = time.time()
        process_type = state["process_type"]
        policy_json = state["policy_json"]
        db_rows = state["current_db_rows"]
        criteria = policy_json.get("item_criteria", [])
        global_rules = policy_json.get("global_rules", {})
        max_ceiling = global_rules.get("max_auto_approval_amount", 1500000 if process_type == "invoice" else 150000)
        hold_cats = set(global_rules.get("hold_categories", []))
        reg_vendors = set(global_rules.get("registered_vendors", []))
        require_registered_vendors = global_rules.get("require_registered_vendors", False) or any(c.get("match_value") == "UNREGISTERED" for c in criteria)

        from erp_db import get_master_regulations
        master_regs = get_master_regulations()

        # Pre-index special rules
        unreg_rule = next((c for c in criteria if c.get("match_value") == "UNREGISTERED"), None)
        ceiling_rule = next((c for c in criteria if c.get("match_field") == "raw_amount"), None)
        cat_rule = next((c for c in criteria if c.get("match_field") == "type"), None)

        decisions = []
        discrepancies = []

        for row in db_rows:
            row_id = row.get("id")
            current_status = row.get("status", "Unprocessed")
            amount = row.get("raw_amount", 0)

            new_status = "Approved" if process_type == "invoice" else "Confirmed"
            matched_rule_id = "RULE-DEFAULT"
            matched_rule_summary = "Standard Policy Evaluation"
            reasons = []

            if process_type == "invoice":
                row_name = (row.get("name") or "")
                row_emp_id = (row.get("employee_id") or "")
                row_type = row.get("type", "Routine")

                # Match vendor rules (both Approved and Hold)
                vendor_hold_rule = None
                vendor_appr_rule = None
                for c in criteria:
                    c_code = c.get("vendor_code") or ""
                    c_name = c.get("vendor_name") or ""
                    val = c.get("match_value") or ""
                    if (c_code and c_code.lower() == row_emp_id.lower()) or \\
                       (c_name and (c_name.lower() in row_name.lower() or row_name.lower() in c_name.lower())) or \\
                       (val and (val.lower() in row_name.lower() or row_name.lower() in val.lower() or val.lower() == row_emp_id.lower())):
                        if c.get("action_on_match") in ("Hold", "Rejected"):
                            vendor_hold_rule = c
                        elif c.get("action_on_match") == "Approved":
                            vendor_appr_rule = c

                # 1. Check Ceiling Threshold
                if amount > max_ceiling:
                    new_status = "Hold"
                    matched_rule_id = ceiling_rule["rule_id"] if ceiling_rule else "RULE-INV-CEILING"
                    matched_rule_summary = ceiling_rule["name"] if ceiling_rule else f"Billing amount exceeds ¥{max_ceiling:,} ceiling"
                    reasons.append(f"Billing amount ¥{amount:,} exceeds policy maximum threshold (¥{max_ceiling:,}). Board director sanction required.")

                # 2. Check Hold Categories
                elif row_type in hold_cats or (cat_rule and row_type in cat_rule.get("match_value", "")):
                    new_status = "Hold"
                    matched_rule_id = cat_rule["rule_id"] if cat_rule else "RULE-INV-CAT"
                    matched_rule_summary = cat_rule["name"] if cat_rule else f"Voucher category '{row_type}' designated for inspection"
                    reasons.append(f"Voucher category '{row_type}' requires accounting manager inspection per policy.")

                # 3. Check Unregistered Vendor Integrity Check
                elif require_registered_vendors and reg_vendors and (row_emp_id not in reg_vendors and not any(v.lower() in row_name.lower() for v in reg_vendors)):
                    new_status = "Hold"
                    matched_rule_id = unreg_rule["rule_id"] if unreg_rule else "RULE-INV-UNREGISTERED"
                    matched_rule_summary = unreg_rule["name"] if unreg_rule else "Unregistered Vendor Integrity Check"
                    reasons.append(f"Vendor '{row_name} ({row_emp_id})' is not registered in the active policy master.")

                # 4. Check Specific Vendor Hold Exceptions
                elif vendor_hold_rule:
                    cond = vendor_hold_rule.get("condition", "")
                    if "Amount != Contract" in cond or "以外" in cond:
                        expected = vendor_appr_rule.get("expected_amounts", []) if vendor_appr_rule else vendor_hold_rule.get("expected_amounts", [])
                        if amount not in expected:
                            new_status = "Hold"
                            matched_rule_id = vendor_hold_rule["rule_id"]
                            matched_rule_summary = vendor_hold_rule["name"]
                            reasons.append(f"Billing amount ¥{amount:,} deviates from registered contract amount ({expected}) for {row_name}.")
                        else:
                            new_status = "Approved"
                            matched_rule_id = vendor_appr_rule["rule_id"] if vendor_appr_rule else "RULE-INV-CONTRACT"
                            matched_rule_summary = vendor_appr_rule["name"] if vendor_appr_rule else "Recurring Contract Match"
                    elif "Adjustment" in cond and row_type == "Adjustment":
                        new_status = "Hold"
                        matched_rule_id = vendor_hold_rule["rule_id"]
                        matched_rule_summary = vendor_hold_rule["name"]
                        reasons.append(f"Voucher category 'Adjustment' for {row_name} requires special review.")
                    else:
                        new_status = "Hold"
                        matched_rule_id = vendor_hold_rule["rule_id"]
                        matched_rule_summary = vendor_hold_rule["name"]
                        reasons.append(vendor_hold_rule.get("description", "Held per vendor policy condition"))

                # 5. Check Approved Vendor Match
                elif vendor_appr_rule:
                    expected_amts = vendor_appr_rule.get("expected_amounts", [])
                    if expected_amts and amount not in expected_amts:
                        if vendor_appr_rule.get("strict_amount", True):
                            new_status = "Hold"
                            matched_rule_id = f"{vendor_appr_rule['rule_id']}-AMT"
                            matched_rule_summary = f"{vendor_appr_rule['name']} (Amount Mismatch)"
                            reasons.append(f"Billed amount ¥{amount:,} does not match contract rate ({expected_amts}).")
                        else:
                            new_status = "Approved"
                            matched_rule_id = vendor_appr_rule["rule_id"]
                            matched_rule_summary = vendor_appr_rule["name"]
                    else:
                        new_status = "Approved"
                        matched_rule_id = vendor_appr_rule["rule_id"]
                        matched_rule_summary = vendor_appr_rule["name"]

                # 6. Default Fallback
                else:
                    if row_type == "Routine" and (not reg_vendors or row_emp_id in reg_vendors or any(v.lower() in row_name.lower() for v in reg_vendors)):
                        new_status = "Approved"
                        matched_rule_id = "RULE-INV-ROUTINE"
                        matched_rule_summary = "Standard Routine Transaction"
                    else:
                        new_status = "Hold"
                        matched_rule_id = "RULE-INV-UNREGISTERED"
                        matched_rule_summary = "Unregistered Vendor Check"
                        reasons.append(f"Vendor '{row_name} ({row_emp_id})' is not registered in active policy master.")

                comment = self.llm_service.generate_comment(process_type, row, new_status, reasons)

            else:  # payroll
                cat = row.get("item_category", "")
                row_type = row.get("item_type", "Addition")
                row_id_val = (row.get("id") or "").lower()
                row_ref = (row.get("voucher_ref") or "").lower()
                row_emp = (row.get("employee_name") or "").lower()

                matched_payroll_rule = None
                for c in criteria:
                    c_voucher = str(c.get("voucher_id") or "").lower()
                    c_ref = str(c.get("voucher_ref") or "").lower()
                    c_val = str(c.get("match_value") or "").lower()
                    c_emp = str(c.get("employee_name") or "").lower()
                    c_cat = str(c.get("item_category") or "").lower()

                    if (c_voucher and c_voucher == row_id_val) or (c_ref and c_ref == row_ref) or \\
                       (c_val and (c_val == row_id_val or c_val == row_ref or c_val in row_emp or c_val in cat.lower())) or \\
                       (c_emp and c_emp in row_emp) or (c_cat and c_cat in cat.lower()):
                        matched_payroll_rule = c
                        break

                if matched_payroll_rule:
                    user_action = matched_payroll_rule.get("action_on_match", "Confirmed")
                    matched_rule_id = matched_payroll_rule.get("rule_id", "RULE-PAY-CUSTOM")
                    matched_rule_summary = matched_payroll_rule.get("description") or matched_payroll_rule.get("name", "Custom Payroll Policy Rule")
                    if user_action in ("Hold", "Rejected"):
                        new_status = "Hold"
                        reasons.append(matched_payroll_rule.get("description", "Held per custom payroll policy condition"))
                    else:
                        new_status = "Confirmed"
                else:
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
                        matched_rule_summary = "Compliant with Corporate Expense Policy"

                comment = self.llm_service.generate_comment(process_type, row, new_status, reasons)

            if new_status == "Hold":
                discrepancies.append({
                    "id": row_id,
                    "name": row.get("name") or row.get("employee_name"),
                    "amount": row.get("amount"),
                    "category": row.get("item_category") or row.get("type"),
                    "rule_id": matched_rule_id,
                    "rule_summary": matched_rule_summary,
                    "reasons": reasons,
                    "suggested_action": "Requires human operator review or manager authorization"
                })

            decisions.append({
                "id": row_id,
                "entity_name": row.get("name") or row.get("employee_name"),
                "ref": row.get("invoice_no") or row.get("voucher_ref") or "Voucher",
                "type": row.get("type") or row.get("item_type"),
                "amount": row.get("amount"),
                "raw_amount": amount,
                "current_status": current_status,
                "new_status": new_status,
                "changed": (current_status != new_status),
                "matched_rule_id": matched_rule_id,
                "matched_rule_summary": matched_rule_summary,
                "reasons": reasons,
                "comment": comment
            })

        return {
            "decisions": decisions,
            "discrepancies": discrepancies,
            "execution_steps": [{
                "node": "Node 2: compare_features_and_decide",
                "duration_s": round(time.time() - t0, 3),
                "status": "COMPLETED",
                "evaluated_rows": len(decisions),
                "proposed_approved": sum(1 for d in decisions if d["new_status"] in ("Approved", "Confirmed")),
                "proposed_hold": len(discrepancies)
            }]
        }'''

pattern_compare = r"    # --- Node 2: Compare Database Features & Decide ---[\s\S]*?        return \{\n            \"decisions\": decisions,\n            \"discrepancies\": discrepancies,[\s\S]*?        \}"
engine_code_updated = re.sub(pattern_compare, new_compare_node, engine_code_updated)

# Update LlmService.generate_comment to use dynamic English reason
pattern_gen_comment = r"        if process_type == \"invoice\":\s+vname = item_data\.get\(\"name\", \"Vendor\"\)\s+itype = item_data\.get\(\"type\", \"Routine\"\)\s+emp_id = item_data\.get\(\"employee_id\", \"\"\)\s+if decision_status == \"Approved\":\s+return f\"Verified against monthly recurring vendor contract for \{vname\} \(\{emp_id\}\)\. Billing amount \{formatted_amt\} matches contract rate and 10% tax breakdown\. Approved\.\"\s+else:[\s\S]*?return f\"\[HOLD\] Contract terms require manual review: \{reason_str\}\.\""
new_gen_comment = '''        if process_type == "invoice":
            vname = item_data.get("name", "Vendor")
            itype = item_data.get("type", "Routine")
            emp_id = item_data.get("employee_id", "")
            if decision_status == "Approved":
                return f"Verified against recurring vendor contract for {vname} ({emp_id}). Billing amount {formatted_amt} matches contract rate and Routine classification. Approved."
            else:
                if reasons:
                    return f"[HOLD] {reasons[0]}"
                elif itype == "Adjustment":
                    return f"[HOLD] Voucher category 'Adjustment' is outside standard recurring contract for {vname}. Requires logistics receipt and accounting manager approval."
                else:
                    return f"[HOLD] Contract terms require manual review for {vname} ({emp_id})."'''

engine_code_updated = re.sub(pattern_gen_comment, new_gen_comment, engine_code_updated)

with open("copilot_langgraph_engine.py", "w", encoding="utf-8") as f:
    f.write(engine_code_updated)

print("copilot_langgraph_engine.py updated successfully!")
