import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

session_path = r"uploads\folder_1792763589_5f62af\ses_20260630-121953-LAPTOP-R36BQBTE"

print("--- GT.JSONL lines containing 175009 ---")
try:
    with open(f"{session_path}\\gt.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if "175009" in line:
                print(line.strip())
except Exception as e:
    print("Error reading gt.jsonl:", e)

print("\n--- GT_MANIFEST.JSON for 175009 ---")
try:
    with open(f"{session_path}\\gt_manifest.json", "r", encoding="utf-8") as f:
        gt = json.load(f)
        for p in gt.get("processes", []):
            code = p.get("code")
            family = p.get("family_name")
            for e in p.get("executions", []):
                cid = str(e.get("case_id", ""))
                if "175009" in cid:
                    print(f"Process: {code} ({family}) | Case: {cid} | Start: {e.get('start_ts')} | End: {e.get('end_ts')}")
except Exception as e:
    print("Error reading gt_manifest.json:", e)
