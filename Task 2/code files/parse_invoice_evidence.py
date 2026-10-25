import sys, json

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

with open(r"c:\Users\KISHORE S\Desktop\pulled_tmi\invoice_multimodal_evidence.json", encoding="utf-8") as f:
    cases = json.load(f)

print(f"Total Cases: {len(cases)}")
for idx, c in enumerate(cases, 1):
    cid = c["case_id"]
    op = c["operator"]
    dur = c["duration_seconds"]
    acts = c["action_sequence"]
    ocr = c["ocr_keyframe_extractions"]
    
    print("=" * 80)
    print(f"Case {idx}: {cid} | Operator: {op} | Duration: {dur}s | Actions: {len(acts)} | OCR Frames: {len(ocr)}")
    print("=" * 80)
    
    print("Key Action Sequence:")
    for a in acts[:8]:
        atype = a.get("action_type")
        app = a.get("app")
        wt = a.get("window_title", "")[:35]
        if atype == "CLICK":
            print(f"  * CLICK: [{a.get('target_text')}] in {app} ({wt})")
        elif atype == "APP_SWITCH":
            print(f"  * SWITCH: to {a.get('to_app')} ({a.get('new_title', '')[:35]})")
        elif atype == "CLIPBOARD_PASTE":
            print(f"  * PASTE: clipboard (length={a.get('length')}) into {app}")
        elif atype == "KEYSTROKE" and a.get("char") and a.get("char") not in ("None", ""):
            print(f"  * TYPE: '{a.get('char')}' in {app}")
        elif atype == "NAVIGATE":
            print(f"  * NAV: to {a.get('url')}")
            
    print("\nSample OCR Lines from Screenshots:")
    for f, lines in list(ocr.items())[:2]:
        print(f"  Frame {f}:")
        for l in lines[:3]:
            print(f"    - {l}")
