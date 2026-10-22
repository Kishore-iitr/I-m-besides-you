import os
import sys
import json
import re
from pathlib import Path
from collections import Counter, defaultdict

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

dataset_dir = Path(r"G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_a")
sessions = [
    "ses_20260701-053005-MSI",
    "ses_20260630-131729-CHAITANYA0BCF",
    "ses_20260701-062250-Marcos",
    "ses_20260701-075604-LAPTOP-0IM1OHQH"
]

UNIVERSAL_CASE_REGEX = re.compile(r'(?:([A-Z]{2,6})[-_](\d{4,8})[-_](\d{2,5})|(BATCH[-_]W\d+))\b')
BLOCKED_APPS = {"procmine-desktop-agent.exe", "procmine-desktop-agent", "omapsvcbroker.exe"}

print("================================================================================")
print("DRY-RUN VALIDATION FOR 4 DISTINCT USER SESSIONS")
print("================================================================================")

for sname in sessions:
    sdir = dataset_dir / sname
    chunk_dirs = sorted([p for p in sdir.iterdir() if p.is_dir() and "chunk" in p.name and (p / "events.jsonl").exists()])
    raw_events = []
    for cdir in chunk_dirs:
        with open(cdir / "events.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    raw_events.append(json.loads(line))
    raw_events.sort(key=lambda x: x.get("timestamp_ms", 0))

    clean_events = []
    for ev in raw_events:
        if ev.get("layer") == "SYSTEM": continue
        ctx = ev.get("context", {}) or {}
        act = ctx.get("active_app", {}) or {}
        pname = (act.get("process_name") or "").lower()
        aname = (act.get("app_name") or "").lower()
        if pname in BLOCKED_APPS or aname in BLOCKED_APPS: continue
        clean_events.append(ev)

    # Ground truth
    gt_file = sdir / "gt.jsonl"
    gt_cases = []
    if gt_file.exists():
        with open(gt_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    gt_cases.append(json.loads(line))

    # Detect batch
    batch_diversity = defaultdict(set)
    for ev in clean_events:
        ctx = ev.get("context", {}) or {}
        act = ctx.get("active_app", {}) or {}
        text = " ".join([act.get("window_title", ""), str(ctx.get("extracted_text", "")), str(ev.get("payload", {}))])
        for m in UNIVERSAL_CASE_REGEX.finditer(text):
            if m.group(1):
                batch_diversity[m.group(2)].add(m.group(1).upper())
            else:
                batch_diversity[m.group(4)].add("BATCH")
    dominant_batch = max(batch_diversity.keys(), key=lambda b: len(batch_diversity[b])) if batch_diversity else "2026"

    # Episode discovery
    debounce_ms = 15000
    raw_episodes = []
    for i, ev in enumerate(clean_events):
        etype = ev.get("event_type")
        payload = ev.get("payload", {}) or {}
        ts_ms = ev.get("timestamp_ms", 0)
        found_cid = None
        if etype in ("browser_click", "mouse_click"):
            elem = payload.get("element") or payload.get("target_element") or {}
            sel = f"{elem.get('css_selector', '')} {elem.get('xpath', '')} {elem.get('text', '')} {elem.get('automation_id', '')} {elem.get('name', '')}"
            m = UNIVERSAL_CASE_REGEX.search(sel)
            if not m:
                ext_str = json.dumps(ev.get("extensions", {}), ensure_ascii=False)
                m = UNIVERSAL_CASE_REGEX.search(ext_str)
            if m:
                found_cid = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m.group(1) else m.group(4)

        is_nav = False
        nav_url = ""
        if etype == "browser_navigation":
            url = payload.get("url") or ""
            if url and not url.endswith(("dashboard", "login", ":5122/", ":5123/", ":5124/", ":5132/", ":5133/", ":5134/")):
                if "sso" not in url and not url.startswith("https://"):
                    is_nav = True
                    nav_url = url

        should_start = False
        if is_nav:
            if not raw_episodes or (ts_ms - raw_episodes[-1]["start_ms"] > debounce_ms):
                should_start = True
        elif found_cid:
            if not raw_episodes:
                should_start = True
            elif raw_episodes[-1].get("cid") is None and (ts_ms - raw_episodes[-1]["start_ms"] < debounce_ms):
                raw_episodes[-1]["cid"] = found_cid
            elif raw_episodes[-1].get("cid") != found_cid and (ts_ms - raw_episodes[-1]["start_ms"] > debounce_ms):
                should_start = True

        if should_start:
            raw_episodes.append({"start_idx": i, "start_ms": ts_ms, "cid": found_cid, "nav_url": nav_url})

    print(f"Session: {sname}")
    print(f"  Clean Events: {len(clean_events)} | Dominant Batch: {dominant_batch}")
    print(f"  Discovered Episodes: {len(raw_episodes)} | Ground Truth Cases: {len(gt_cases)}")
    print("--------------------------------------------------------------------------------")

print("\nGROUND TRUTH MANIFEST AUDIT:")
for sname in sessions:
    mf = dataset_dir / sname / "gt_manifest.json"
    if mf.exists():
        with open(mf, "r", encoding="utf-8") as f:
            d = json.load(f)
            total_exec = sum(len(p.get("executions", [])) for p in d.get("processes", []))
            print(f"Session {sname}: {total_exec} GT executions across {len(d.get('processes', []))} processes")
            for p in d.get("processes", []):
                print(f"   Process {p.get('code')}: {p.get('family_name')} ({len(p.get('executions', []))} cases)")
    else:
        print(f"Session {sname}: NO gt_manifest.json")
