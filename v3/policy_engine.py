"""
Policy Engine: Shared rule extraction and evaluation for Invoice Processing (English Edition).
Used by both automation_portal.py and erp_web_app.py.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Tuple

POLICY_FILE = Path(__file__).parent / "active_policy.json"

DEFAULT_POLICIES = {
    "getsujitsu_teigaku_torihikisaki_ichiran": {
        "id": "getsujitsu_teigaku_torihikisaki_ichiran",
        "title": "Monthly Fixed-Price Vendor Policy",
        "type": "fixed_vendor",
        "description": "5-Vendor Master Reconciliation Policy (Yamada, Yamato, Tokyo Electronics, Global Tech, Hokuriku Parts)",
        "summary": "Monthly fixed-price contracts. Invoices are approved ONLY if vendor name and billing amount match the agreed contract amount exactly. Mismatches or unlisted vendors are placed On Hold.",
        "vendors": {
            "Yamada Manufacturing Co., Ltd.": 385000,
            "株式会社山田製作所": 385000,
            "Yamato Shoji Co., Ltd.": 1240000,
            "大和商事株式会社": 1240000,
            "Tokyo Electronics Industry Co., Ltd.": 562800,
            "東京電子工業株式会社": 562800,
            "Global Tech LLC": 745000,
            "グローバルテック合同会社": 745000,
            "Hokuriku Parts Industry Co., Ltd.": 420000,
            "北陸電子部品": 420000,
            "北陸部品工業株式会社": 420000
        },
        "approve_comment": "Monthly fixed-price vendor list reconciled. Invoice amount and consumption tax verified.",
        "hold_mismatch_comment": "Contract amount mismatch (Contract: ¥{expected} / Invoiced: ¥{actual}). On hold for verification.",
        "hold_unregistered_comment": "Unregistered vendor (Not in fixed contract list). On hold for verification."
    },
    "shinkui_keiyaku_tetsuzuki": {
        "id": "shinkui_keiyaku_tetsuzuki",
        "title": "New Vendor Contract Procedure Policy",
        "type": "new_contract",
        "description": "Initial invoice approval procedure & ¥1,000,000 sign-off threshold",
        "summary": "Invoices under ¥1,000,000 can be approved under Department Manager authority. Invoices of ¥1,000,000 or greater require Executive approval and are placed On Hold at the accounting review stage.",
        "threshold": 1000000,
        "approve_comment": "New contract procedure verified. Approved under Department Manager authority.",
        "hold_over_threshold_comment": "New contract exceeds ¥1,000,000 threshold. On hold for Executive sign-off."
    },
    "keiyaku_kaijo_tetsuzuki": {
        "id": "keiyaku_kaijo_tetsuzuki",
        "title": "Contract Termination & Settlement Policy",
        "type": "termination",
        "description": "Procedure for terminated or exiting vendor debt reconciliation",
        "summary": "Invoices received from vendors undergoing contract termination must NOT be approved immediately. Placed On Hold pending final settlement of outstanding debts and prepaid fees.",
        "hold_comment": "Contract termination in progress. On hold pending final debt settlement."
    },
    "it_gyomu_butsuryu_shinsa": {
        "id": "it_gyomu_butsuryu_shinsa",
        "title": "IT Outsourcing & Logistics Audit Policy",
        "type": "custom_it_logistics",
        "description": "Fukuoka System Design (¥2M cap), Okinawa Logistics (¥500k adjustment), Hokuriku Inspection audit",
        "summary": "Fukuoka System Design is approved if under ¥2,000,000 monthly budget. Okinawa Logistics is approved if under ¥500,000 adjustment. Hokuriku Parts adjustments are held for inspection report. Routine suppliers are held as out-of-scope.",
        "approve_fukuoka": "IT service contract verified. Milestones accepted and within monthly budget.",
        "hold_fukuoka_over": "IT development budget exceeded (Over ¥2,000,000). On hold for approval.",
        "approve_okinawa": "Logistics warehouse adjustment verified against breakdown. Approved.",
        "hold_hokuriku_adj": "Manufacturing adjustment. On hold pending quality inspection report.",
        "hold_other": "Outside special IT/Logistics scope. Forwarded to standard routine audit."
    }
}

def get_active_policy() -> Dict[str, Any]:
    if POLICY_FILE.exists():
        try:
            with open(POLICY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_POLICIES["getsujitsu_teigaku_torihikisaki_ichiran"]

def set_active_policy(policy_data: Dict[str, Any]):
    with open(POLICY_FILE, "w", encoding="utf-8") as f:
        json.dump(policy_data, f, ensure_ascii=False, indent=2)

def evaluate_invoice(policy: Dict[str, Any], inv: Dict[str, Any]) -> Tuple[str, str, str]:
    """
    Evaluates an invoice dict against the policy dict.
    Returns: (decision: 'Approved'|'On Hold', comment: str, reason: str)
    """
    name = inv.get("name", "").strip()
    raw_amount = int(inv.get("raw_amount") or 0)
    ptype = policy.get("type", "fixed_vendor")

    if ptype == "fixed_vendor":
        vendors = policy.get("vendors", {})
        matched_vendor = None
        for v in vendors:
            if v.lower() in name.lower() or name.lower() in v.lower():
                matched_vendor = v
                break
        
        if not matched_vendor:
            return "On Hold", policy.get("hold_unregistered_comment", "Unregistered vendor (Not in fixed contract list). On hold for verification."), f"Unregistered vendor ({name})"
        
        expected = vendors[matched_vendor]
        if raw_amount == expected:
            return "Approved", policy.get("approve_comment", "Monthly fixed-price vendor list reconciled. Invoice amount and consumption tax verified."), f"Exact amount match (¥{expected:,})"
        else:
            comment_template = policy.get("hold_mismatch_comment", "Contract amount mismatch. On hold.")
            comment = comment_template.replace("{expected}", f"{expected:,}").replace("{actual}", f"{raw_amount:,}")
            return "On Hold", comment, f"Amount discrepancy (Contract: ¥{expected:,} / Invoiced: ¥{raw_amount:,})"

    elif ptype == "new_contract":
        threshold = int(policy.get("threshold", 1000000))
        if raw_amount < threshold:
            return "Approved", policy.get("approve_comment", "New contract procedure verified. Approved under Department Manager authority."), f"Under ¥1M (¥{raw_amount:,} < ¥{threshold:,})"
        else:
            return "On Hold", policy.get("hold_over_threshold_comment", "New contract exceeds ¥1,000,000 threshold. On hold for Executive sign-off."), f"Exceeds ¥1M (¥{raw_amount:,} >= ¥{threshold:,})"

    elif ptype == "termination":
        return "On Hold", policy.get("hold_comment", "Contract termination in progress. On hold pending final debt settlement."), "Terminated vendor settlement"

    elif ptype == "custom_it_logistics":
        name_lower = name.lower()
        if "fukuoka" in name_lower or "福岡" in name:
            if raw_amount < 2000000:
                return "Approved", policy.get("approve_fukuoka", "IT service contract verified. Milestones accepted and within monthly budget."), f"Fukuoka System Design under ¥2M (¥{raw_amount:,})"
            else:
                return "On Hold", policy.get("hold_fukuoka_over", "IT development budget exceeded (Over ¥2,000,000). On hold for approval."), f"Fukuoka System Design exceeds ¥2M (¥{raw_amount:,})"
        elif "okinawa" in name_lower or "沖縄" in name:
            itype = str(inv.get("type", "")).lower()
            if ("adjustment" in itype or "調整" in itype) and raw_amount < 500000:
                return "Approved", policy.get("approve_okinawa", "Logistics warehouse adjustment verified against breakdown. Approved."), f"Okinawa Logistics adjustment under ¥500k (¥{raw_amount:,})"
            else:
                return "On Hold", "Logistics adjustment over ¥500k. On hold for Department Manager review.", f"Okinawa Logistics review needed (¥{raw_amount:,})"
        elif ("hokuriku" in name_lower or "北陸" in name) and ("adjustment" in str(inv.get("type", "")).lower() or "調整" in str(inv.get("type", ""))):
            return "On Hold", policy.get("hold_hokuriku_adj", "Manufacturing adjustment. On hold pending quality inspection report."), "Hokuriku Parts inspection report pending"
        else:
            return "On Hold", policy.get("hold_other", "Outside special IT/Logistics scope. Forwarded to standard routine audit."), f"Out of scope vendor ({name})"

    # Default fallback
    return "On Hold", "On hold for verification", "No matching policy rule"

# Initialize default active policy file
set_active_policy(DEFAULT_POLICIES["getsujitsu_teigaku_torihikisaki_ichiran"])
