import glob
import json
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

print("Searching OCR checkpoints for expense_calc...")

for f in glob.glob("checkpoints/stage0_ocr_*.json"):
    with open(f, "r", encoding="utf-8") as fp:
        data = json.load(fp)
        ocr_results = data if isinstance(data, list) else data.get("ocr_results", [])
        for item in ocr_results:
            text = item.get("ocr_text", "")
            wt = item.get("window_title", "")
            if "expense_calc" in wt.lower() or "expense_calc" in text.lower():
                print(f"\nFile: {f} | Window: {wt}")
                print(f"OCR snippet: {text[:300]}")
                break
