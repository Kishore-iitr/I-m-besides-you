import re
import json

prompt_text = """月次定期サービス・外注業務委託照合基準 (2026年度 下半期 財務経理部門)
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

def parse_arbitrary_policy(process_type: str, text: str):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    current_section = "GENERAL"
    rules = []
    registered_vendors = set()
    global_rules = {
        "max_auto_approval_amount": 2000000,
        "require_comment": True,
        "hold_categories": [],
        "allowed_routine_categories": ["Routine"]
    }

    rule_idx = 1

    for line in lines:
        # 1. Section Header Detection
        if any(kw in line for kw in ["【自動承認", "【承認", "Auto-Approved", "Approved Rules", "対象ベンダー"]):
            current_section = "APPROVED"
            continue
        elif any(kw in line for kw in ["【保留", "【要人間精査", "Hold / Review", "例外保留", "除外"]):
            current_section = "HOLD"
            continue

        # Extract amounts in current line
        amts = [int(x.replace(',', '')) for x in re.findall(r'[¥\\]\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,9})', line)]
        if not amts:
            amts = [int(x.replace(',', '')) for x in re.findall(r'([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,9})\s*円', line)]

        # Check vendor code (e.g. V1001, V3005) or vendor name
        v_match = re.search(r'([A-Za-z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\s\.\,\-]+?)\s*\(([A-Z][0-9]{3,5})\)', line)
        v_code_only = re.search(r'\b([A-Z][0-9]{3,5})\b', line)
        
        # Check action in line
        has_hold = any(kw in line for kw in ["Hold", "保留", "要確認", "超", "除外", "精査", "不整合", "差戻し", "以外"])
        has_appr = any(kw in line for kw in ["Approved", "承認", "確定", "固定", "Confirmed", "適合", "範囲内"])

        if has_hold and not has_appr:
            line_action = "Hold"
        elif has_appr and not has_hold:
            line_action = "Approved" if process_type == "invoice" else "Confirmed"
        else:
            line_action = "Hold" if current_section == "HOLD" else ("Approved" if process_type == "invoice" else "Confirmed")

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
        if any(kw in line for kw in ["区分条件", "区分（Category）", "処理区分", "Category"]) and any(kw in line for kw in ["Adjustment", "Spot", "Routine", "手当"]):
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
        if v_match or v_code_only or (process_type == "payroll" and re.search(r'P[0-9]\-[0-9]{8}\-[0-9]{3}', line)):
            v_name = v_match.group(1).strip() if v_match else ""
            v_code = v_match.group(2).strip() if v_match else (v_code_only.group(1).strip() if v_code_only else "")
            
            # Clean v_name from prefixes like "No.1", "1.", etc.
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
                "condition": ", ".join(cond_parts) if cond_parts else f"Policy: {line_action}",
                "action_on_match": line_action,
                "action_on_mismatch": "Approved" if line_action == "Hold" else "Hold",
                "description": line
            })
            rule_idx += 1
            continue

        # --- Rule Case E: General Bullet or Sentence with Category / Amount ---
        if amts or any(kw in line for kw in ["研修", "旅費", "消耗品", "交通費", "接待", "手当", "給与", "委託", "調整"]):
            rules.append({
                "rule_id": f"RULE-{process_type[:3].upper()}-{rule_idx:02d}",
                "name": f"Policy Criterion {rule_idx}",
                "match_field": "description",
                "match_value": line[:30],
                "expected_amounts": amts,
                "expected_amount": amts[0] if amts else None,
                "condition": f"Amount: {' or '.join([f'¥{a:,}' for a in amts])}" if amts else f"Status: {line_action}",
                "action_on_match": line_action,
                "action_on_mismatch": "Hold",
                "description": line
            })
            rule_idx += 1

    return {
        "global_rules": global_rules,
        "registered_vendors": list(registered_vendors),
        "rules": rules
    }

parsed = parse_arbitrary_policy('invoice', prompt_text)
print(f"Total Rules Extracted: {len(parsed['rules'])}")
for r in parsed['rules']:
    desc = r['description'].encode('unicode_escape').decode()
    mv = str(r['match_value']).encode('unicode_escape').decode()
    print(f"  [{r['rule_id']}] {mv:40} | {r['condition']:35} | {r['action_on_match']:8} | {desc}")
