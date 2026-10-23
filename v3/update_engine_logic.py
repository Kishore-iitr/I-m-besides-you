import re

with open("copilot_langgraph_engine.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Normalize line endings to \n
code = code.replace("\r\n", "\n")

# 2. Rule Case D update in _semantic_fallback_extract
old_case_d = """                cond_parts = []
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
                })"""

new_case_d = """                # Construct human-readable, precise condition formula
                if line_action == "Approved":
                    if len(amts) == 1:
                        cond_str = f"Category == 'Routine' && Amount == ¥{amts[0]:,} (Fixed Rate)"
                    elif len(amts) > 1:
                        cond_str = f"Category == 'Routine' && Amount in [{', '.join([f'¥{a:,}' for a in amts])}] (Contract Range)"
                    else:
                        cond_str = "Category == 'Routine' (Contract Rate)"
                else:
                    if "以外" in line and amts:
                        cond_str = f"Vendor == '{v_code}' && Amount != ¥{amts[0]:,} (Non-standard Maintenance -> Hold)"
                    elif "Adjustment" in line:
                        cond_str = f"Vendor == '{v_code}' && Category == 'Adjustment' (Unscheduled Adjustment -> Hold)"
                    elif "Spot" in line:
                        cond_str = f"Vendor == '{v_code}' && Category == 'Spot' (Spot Order Review -> Hold)"
                    else:
                        cond_str = f"Vendor == '{v_code}' (Special Inspection -> Hold)"

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
                    "condition": cond_str,
                    "action_on_match": line_action,
                    "action_on_mismatch": "Approved" if line_action == "Hold" else "Hold",
                    "description": line
                })"""

assert old_case_d in code, "old_case_d not found in code"
code = code.replace(old_case_d, new_case_d)

# 3. Rule Case E update (Payroll)
old_case_e = """                    "condition": f"Voucher: {v_id or 'Target'}, Amount: {f'¥{amts[0]:,}' if amts else 'Within limit'}\","""
new_case_e = """                    "condition": f"Voucher == '{v_id}' && Amount <= ¥{amts[0]:,} (Receipt Matched)" if (v_id and amts) else (f"Category == '{cat_name}' && Amount <= ¥{amts[0]:,}" if amts else f"Category == '{cat_name}' (Policy Standard)"),"""
if old_case_e in code:
    code = code.replace(old_case_e, new_case_e)

# 4. Update evaluate() custom_rules parser
old_eval_custom = """        if custom_rules is not None and len(custom_rules) > 0:
            reg_v = set()
            for r in custom_rules:
                if r.get("vendor_code"):
                    reg_v.add(r["vendor_code"])
                if r.get("vendor_name"):
                    reg_v.add(r["vendor_name"])
            
            ceiling_r = next((r for r in custom_rules if r.get("match_field") == "raw_amount"), None)
            max_c = ceiling_r.get("threshold_amount", 1500000 if process_type == "invoice" else 150000) if ceiling_r else (1500000 if process_type == "invoice" else 150000)

            hold_c = []
            for r in custom_rules:
                if r.get("match_field") == "type" and r.get("action_on_match") in ("Hold", "Rejected"):
                    for w in ["Adjustment", "Spot", "Routine"]:
                        if w in str(r.get("match_value", "")):
                            hold_c.append(w)"""

new_eval_custom = """        if custom_rules is not None and len(custom_rules) > 0:
            reg_v = set()
            hold_c = []
            max_c = 1500000 if process_type == "invoice" else 150000

            for r in custom_rules:
                cond_str = str(r.get("condition", ""))
                mv_str = str(r.get("match_value", ""))
                desc_str = str(r.get("description", ""))
                action = r.get("action_on_match", "Approved")

                # Extract vendor codes (e.g. V1001, V3005)
                v_codes = re.findall(r'\\b([A-Z][0-9]{3,5})\\b', mv_str + " " + cond_str)
                for vc in v_codes:
                    if vc != "UNREGISTERED":
                        r["vendor_code"] = vc
                        reg_v.add(vc)

                # Extract amounts from condition and match_value
                amts = [int(x.replace(',', '')) for x in re.findall(r'[¥\\\\]\\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,9})', cond_str + " " + mv_str)]
                if not amts:
                    amts = [int(x.replace(',', '')) for x in re.findall(r'([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,9})\\s*円', cond_str + " " + mv_str)]
                if not amts:
                    amts = [int(x.replace(',', '')) for x in re.findall(r'\\b([0-9]{4,9})\\b', cond_str + " " + mv_str)]

                if amts:
                    r["expected_amounts"] = amts
                    r["expected_amount"] = amts[0]

                # Check if this rule defines a ceiling
                if any(kw in cond_str.lower() or kw in desc_str.lower() for kw in [">", "超過", "上限", "ceiling", "limit"]):
                    if amts:
                        r["threshold_amount"] = amts[0]
                        r["match_field"] = "raw_amount"
                        max_c = amts[0]

                # Check if this rule defines categories to hold
                if action in ("Hold", "Rejected"):
                    for cat in ["Adjustment", "Spot", "Routine", "Entertainment", "手当", "控除"]:
                        if cat in cond_str or cat in mv_str or cat in desc_str:
                            if cat not in hold_c:
                                hold_c.append(cat)
                            r["match_field"] = "type"

                # Check strict amount / exception hold flags
                if any(kw in cond_str or kw in desc_str for kw in ["!=", "以外", "不一致", "固定", "fixed"]):
                    r["strict_amount"] = True
                    if action in ("Hold", "Rejected"):
                        r["is_exception_hold"] = True

                # If vendor name exists
                if r.get("name"):
                    reg_v.add(r["name"])"""

assert old_eval_custom in code, "old_eval_custom not found in code"
code = code.replace(old_eval_custom, new_eval_custom)

with open("copilot_langgraph_engine.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Successfully updated copilot_langgraph_engine.py!")
