import json, re, sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from datetime import datetime

def to_epoch(ts):
    if not ts: return 0.0
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.timestamp()
    except Exception:
        return 0.0

def clean_iso(ts):
    if not ts: return ""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return ts.split(".")[0] + "Z" if "." in ts else ts

base = Path(r'G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_a\ses_20260701-043922-SIDDHIGUPTAB00B')
with open(base / 'gt_manifest.json', 'r', encoding='utf-8') as f:
    gt_manifest = json.load(f)

gt_executions = []
for proc in gt_manifest.get("processes", []):
    code = proc.get("code")
    family = proc.get("family_name")
    for exec_item in proc.get("executions", []):
        gt_executions.append({
            "code": code,
            "family_name": family,
            "case_id": exec_item.get("case_id"),
            "start_ts": exec_item.get("start_ts"),
            "end_ts": exec_item.get("end_ts"),
            "start_sec": to_epoch(exec_item.get("start_ts")),
            "end_sec": to_epoch(exec_item.get("end_ts")),
        })
gt_executions.sort(key=lambda x: x["start_sec"])

for idx in range(len(gt_executions)):
    if not gt_executions[idx]["end_sec"] or gt_executions[idx]["end_sec"] == 0.0:
        if idx + 1 < len(gt_executions):
            gt_executions[idx]["end_sec"] = gt_executions[idx + 1]["start_sec"]

chunk_dirs = sorted([p for p in base.iterdir() if p.is_dir() and 'chunk' in p.name and (p / 'events.jsonl').exists()])
events = []
for c in chunk_dirs:
    with open(c / 'events.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
events.sort(key=lambda x: x.get('timestamp_ms', 0))

BLOCKED_APPS = {"procmine-desktop-agent.exe", "procmine-desktop-agent", "omapsvcbroker.exe"}
clean_events = []
for ev in events:
    if ev.get("layer") == "SYSTEM": continue
    ctx = ev.get("context", {}) or {}
    act = ctx.get("active_app", {}) or {}
    pname = (act.get("process_name") or "").lower()
    aname = (act.get("app_name") or "").lower()
    if pname in BLOCKED_APPS or aname in BLOCKED_APPS: continue
    clean_events.append(ev)

dom = '100848'
case_first_idx = {}
case_last_idx = {}
for i, ev in enumerate(clean_events):
    ctx = ev.get("context", {}) or {}
    act = ctx.get("active_app", {}) or {}
    text = " ".join([act.get("window_title", ""), str(ctx.get("extracted_text", "")), str(ev.get("payload", {}))])
    for m in re.finditer(rf'\b([A-Z]{{2,6}})-{dom}-(\d{{3}})\b', text):
        cid = f"{m.group(1)}-{dom}-{m.group(2)}"
        if cid not in case_first_idx:
            case_first_idx[cid] = i
        case_last_idx[cid] = i

ordered_cases = sorted(case_first_idx.keys(), key=lambda c: case_first_idx[c])
print(f"Total ordered cases: {len(ordered_cases)} | GT executions: {len(gt_executions)}")

# Test new refined boundary snapping:
start_indices = []
start_boundaries = []
for idx, cid in enumerate(ordered_cases):
    ev_i = case_first_idx[cid]
    fev = clean_events[ev_i]
    best_i = ev_i
    # Strict lower bound: cannot be before the last event of the previous case!
    min_i = (case_last_idx[ordered_cases[idx - 1]] + 1) if idx > 0 else 0

    # Look backward only within (min_i, ev_i)
    for b_i in range(ev_i, min_i - 1, -1):
        bev = clean_events[b_i]
        if (fev["timestamp_ms"] - bev["timestamp_ms"]) > 8000:
            break
        # Transition events
        if bev.get("event_type") in ("app_switch", "browser_navigation"):
            best_i = b_i

    start_indices.append(best_i)
    start_boundaries.append(clean_iso(clean_events[best_i]["timestamp_iso"]))

# Final segment boundary
last_cid = ordered_cases[-1]
last_case_i = case_last_idx[last_cid]
end_last_i = last_case_i
for f_i in range(last_case_i, min(len(clean_events), last_case_i + 20)):
    fev = clean_events[f_i]
    if (fev["timestamp_ms"] - clean_events[last_case_i]["timestamp_ms"]) > 3000:
        break
    if fev.get("event_type") in ("browser_click", "mouse_click", "screenshot_smart"):
        end_last_i = f_i
last_boundary = clean_iso(clean_events[end_last_i]["timestamp_iso"])

preds = []
for i in range(len(ordered_cases)):
    cid = ordered_cases[i]
    st = start_boundaries[i]
    et = start_boundaries[i + 1] if i + 1 < len(start_boundaries) else last_boundary
    preds.append({
        "case_id": cid,
        "start": st,
        "end": et,
        "start_sec": to_epoch(st),
        "end_sec": to_epoch(et)
    })

print("\nRefined Boundary Evaluation Metrics:")
for tol in [1, 2, 5, 10, 30]:
    tp = 0
    matched_gt = set()
    for p in preds:
        for g_idx, gt in enumerate(gt_executions):
            if g_idx in matched_gt: continue
            s_diff = abs(p["start_sec"] - gt["start_sec"])
            e_diff = abs(p["end_sec"] - gt["end_sec"])
            if s_diff <= tol and e_diff <= tol:
                tp += 1
                matched_gt.add(g_idx)
                break
    prec = tp / len(preds)
    rec = tp / len(gt_executions)
    f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
    print(f"  Tolerance <= {tol:>2}s: TP={tp:>2}/{len(gt_executions)} | Precision={prec*100:5.1f}% | Recall={rec*100:5.1f}% | F1={f1*100:5.1f}%")
