import json
from pathlib import Path
from test_episodes_dryrun import *

sname = "ses_20260701-053005-MSI"
sdir = dataset_dir / sname
# Run episode discovery for MSI
chunk_dirs = sorted([p for p in sdir.iterdir() if p.is_dir() and "chunk" in p.name and (p / "events.jsonl").exists()])
raw_events = []
for cdir in chunk_dirs:
    with open(cdir / "events.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip(): raw_events.append(json.loads(line))
raw_events.sort(key=lambda x: x.get("timestamp_ms", 0))

clean_events = [ev for ev in raw_events if ev.get("layer") != "SYSTEM" and not any(term in (ev.get("context", {}).get("active_app", {}).get("process_name", "") or "").lower() for term in BLOCKED_APPS)]

raw_episodes = []
debounce_ms = 15000
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
        raw_episodes.append({"start_idx": i, "start_ms": ts_ms, "start_iso": ev.get("timestamp_iso"), "cid": found_cid, "nav_url": nav_url})

print(f"Total Discovered Episodes: {len(raw_episodes)}")
for idx, ep in enumerate(raw_episodes, 1):
    print(f"{idx:02d}. CID: {str(ep['cid']):<20} | Time: {ep['start_iso']} | URL: {ep['nav_url']}")
