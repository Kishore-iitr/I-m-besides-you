import glob
import json
import re

all_windows = set()
all_docs = set()
invoice_windows = set()
payroll_windows = set()

for f in glob.glob("segments*.jsonl"):
    print(f"Scanning {f}...")
    with open(f, "r", encoding="utf-8") as fp:
        for line in fp:
            if not line.strip():
                continue
            data = json.loads(line)
            txt = json.dumps(data, ensure_ascii=False)
            
            # documents
            for m in re.findall(r'[\w\-_\.]+\.(?:docx?|xlsx?|txt|csv|pdf)', txt, re.IGNORECASE):
                all_docs.add(m)
                
            # window title from action_events
            events = data.get("action_events") or data.get("events") or []
            for ev in events:
                wt = ev.get("window_title") or ev.get("title") or ""
                if wt:
                    all_windows.add(wt)
                    if "invoice" in txt.lower() or "請求書" in txt:
                        invoice_windows.add(wt)
                    if "payroll" in txt.lower() or "給与" in txt or "精算" in txt:
                        payroll_windows.add(wt)

print("\n--- ALL EXTRACTED DOCUMENT FILENAMES ---")
for d in sorted(all_docs):
    print("  *", d)

print("\n--- WINDOWS IN INVOICE PROCESSING ---")
for w in sorted(invoice_windows):
    if any(k in w.lower() for k in ["word", "excel", "notepad", "edge", "ichiran", "kitei", "memo", "xlsx", "docx"]):
        print("  *", w)

print("\n--- WINDOWS IN PAYROLL PROCESSING ---")
for w in sorted(payroll_windows):
    if any(k in w.lower() for k in ["word", "excel", "notepad", "edge", "ichiran", "kitei", "memo", "xlsx", "docx"]):
        print("  *", w)
