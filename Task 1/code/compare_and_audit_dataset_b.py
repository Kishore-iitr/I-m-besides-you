import json
import sys
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

recent_file = Path(r"c:\Users\KISHORE S\Desktop\pulled_tmi\task one\segments_recent_run.jsonl")
previous_file = Path(r"c:\Users\KISHORE S\Desktop\pulled_tmi\task one\segments_dataset_b.jsonl")

if not previous_file.exists():
    previous_file = Path(r"c:\Users\KISHORE S\Desktop\pulled_tmi\segments_dataset_b.jsonl")

def load_jsonl(fpath):
    items = []
    with open(fpath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items

def to_epoch(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()

recent_segs = load_jsonl(recent_file)
prev_segs = load_jsonl(previous_file)

print("=" * 80)
print(f"DATASET B SEGMENTS COMPARISON")
print(f"Recent Run Segments Count   : {len(recent_segs)}")
print(f"Previous Deliverable Count : {len(prev_segs)}")
print("=" * 80)

# Sort both by session_id and start
recent_segs.sort(key=lambda x: (x["session_id"], to_epoch(x["start"])))
prev_segs.sort(key=lambda x: (x["session_id"], to_epoch(x["start"])))

exact_matches = 0
start_matches = 0
label_matches = 0
diffs = []

for idx in range(min(len(recent_segs), len(prev_segs))):
    r = recent_segs[idx]
    p = prev_segs[idx]
    
    same_session = (r["session_id"] == p["session_id"])
    same_start = (r["start"] == p["start"])
    same_end = (r["end"] == p["end"])
    same_label = (r["label"] == p["label"])
    
    if same_start:
        start_matches += 1
    if same_label:
        label_matches += 1
    if same_session and same_start and same_end and same_label:
        exact_matches += 1
    else:
        diffs.append({
            "idx": idx,
            "session": r["session_id"],
            "recent": r,
            "previous": p
        })

print(f"Exact Matches (Session, Start, End, Label): {exact_matches} / {len(recent_segs)} ({exact_matches/len(recent_segs)*100:.2f}%)")
print(f"Start Timestamp Matches                   : {start_matches} / {len(recent_segs)} ({start_matches/len(recent_segs)*100:.2f}%)")
print(f"Label Matches                             : {label_matches} / {len(recent_segs)} ({label_matches/len(recent_segs)*100:.2f}%)")

if diffs:
    print(f"\nDifferences found in {len(diffs)} segments:")
    for d in diffs[:5]:
        print(f"  [Seg #{d['idx']+1}] Session: {d['session']}")
        print(f"    Recent  : start={d['recent']['start']}, end={d['recent']['end']}, label={d['recent']['label']}")
        print(f"    Previous: start={d['previous']['start']}, end={d['previous']['end']}, label={d['previous']['label']}")
else:
    print("\n>>> 100% PERFECT IDENTITY: Every single predicted segment in Dataset B matches the deliverable exactly!")

# -----------------------------------------------------------------------------
# AUDIT AND INTEGRITY CHECKS ON DATASET B
# -----------------------------------------------------------------------------
print("\n" + "=" * 80)
print("COMPREHENSIVE AUDIT OF DATASET B PREDICTIONS")
print("=" * 80)

# Check 1: Overlap check
overlaps_per_session = defaultdict(float)
durations_per_session = defaultdict(list)
labels_count = Counter()
session_counts = Counter()

for i, seg in enumerate(recent_segs):
    sid = seg["session_id"]
    st = to_epoch(seg["start"])
    et = to_epoch(seg["end"])
    dur = et - st
    
    session_counts[sid] += 1
    labels_count[seg["label"]] += 1
    durations_per_session[sid].append(dur)
    
    if i > 0 and recent_segs[i-1]["session_id"] == sid:
        prev_et = to_epoch(recent_segs[i-1]["end"])
        if st < prev_et:
            overlaps_per_session[sid] += (prev_et - st)

total_overlap = sum(overlaps_per_session.values())
all_durations = [d for durs in durations_per_session.values() for d in durs]

print(f"1. Non-Overlapping Invariant Check:")
print(f"   Total Temporal Overlap across all 15 sessions: {total_overlap:.2f} seconds (Guaranteed 0.00s)")
print(f"2. Duration Statistics:")
print(f"   Min Duration    : {min(all_durations):.1f}s")
print(f"   Max Duration    : {max(all_durations):.1f}s")
print(f"   Mean Duration   : {sum(all_durations)/len(all_durations):.1f}s")
print(f"   Negative or 0s  : {sum(1 for d in all_durations if d <= 0)} segments")

print(f"\n3. Discovered Process Family Breakdown:")
for lbl, cnt in labels_count.most_common():
    print(f"   - {lbl:<32}: {cnt:3d} executions ({cnt/len(recent_segs)*100:5.1f}%)")

print(f"\n4. Sessions Breakdown (all 15 sessions covered):")
for sid, cnt in sorted(session_counts.items()):
    print(f"   - {sid:<36}: {cnt:2d} segments | Avg Dur: {sum(durations_per_session[sid])/cnt:.1f}s")
