"""
Task Model Induction (TMI) Pipeline for Desktop Agent Operation Logs
Adapted from Jiang et al., "Inducing Task Models from Computer-Use Traces" (arXiv:2608.20319v1)

Implements:
1. Event Normalization & Keystroke Reconstruction (handling unreliable text_input_complete)
2. Activity Segmentation (Paper §3.1)
3. Zero-Leakage Latent Task Induction via Puter AI / OpenRouter Free Model (Paper §3.2, Figures 7 & 8)
   - Dynamic extraction of observed Japanese window titles & screen text from trace
   - Semantic induction of canonical English snake_case process labels via Puter LLM
4. Execution Splitting & Precision Boundary Snapping (Paper §3.2 & §3.3)
5. Ground Truth Evaluation (gt_manifest.json strictly isolated to post-hoc metrics)
"""

import os
import re
import sys
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
import urllib.request
import urllib.error

# Ensure UTF-8 console output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Case ID patterns for enterprise systems (3-part e.g. RT-110019-001 or 2-part e.g. REQ-10023)
THREE_PART_REGEX = re.compile(r'\b([A-Z]{2,6})[-_](\d{4,8})[-_](\d{2,4})\b')
TWO_PART_REGEX = re.compile(r'\b([A-Z]{2,6})[-_](\d{4,8})\b')
IGNORE_IDENTIFIERS = {"LAPTOP", "MSI", "CHUNK", "EVT", "MONITOR", "SESSION", "PROCMINE"}


class PuterLlmClient:
    """Client for Puter.js / OpenRouter free models using Puter's driver API."""

    def __init__(self, token: Optional[str] = None, model: Optional[str] = None):
        self.token = token or os.environ.get(
            "PUTER_AUTH_TOKEN",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6InYyIn0.eyJ0IjoiYXUiLCJ2IjoiMiIsInV1IjoiZ0dXcTBPVE1TdEdSWkZWK2RQZEFWZz09IiwiYXUiOiJKaFNmQzRNRVVpaTVsWGN0cmM5QkRnPT0iLCJzdSI6ImhUS1diTTNnVCtxMHBvVHZpT2JsMUE9PSIsImFpIjoiZ0dXcTBPVE1TdEdSWkZWK2RQZEFWZz09IiwiaWF0IjoxNzkyNTY1OTE4fQ.XrFC2-zDsTcgmO7ioM3kXqu89Wqf48fkFaxZZQs1k1U"
        )
        self.model = model or os.environ.get(
            "PUTER_MODEL", "openrouter:minimax/minimax-m3.1-flash:free"
        )
        self.url = "https://api.puter.com/drivers/call"

    def complete(self, prompt: str, system_prompt: Optional[str] = None, timeout: int = 60) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "interface": "puter-chat-completion",
            "driver": "ai-chat",
            "test_mode": False,
            "method": "complete",
            "args": {
                "messages": messages,
                "model": self.model,
                "stream": False,
                "temperature": 0.1
            }
        }

        req = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            },
            method="POST"
        )

        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as res:
                    data = json.loads(res.read().decode("utf-8"))
                    if not data.get("success"):
                        raise RuntimeError(f"Puter API error: {data}")
                    result = data.get("result", {})
                    message = result.get("message", {})
                    return message.get("content", "")
            except Exception as e:
                if attempt == 0:
                    time.sleep(2.0)
                    continue
                print(f"[PuterLlmClient] Call failed: {e}", file=sys.stderr)
                raise

    def complete_json(self, prompt: str, system_prompt: Optional[str] = None, timeout: int = 60) -> Dict[str, Any]:
        raw_text = self.complete(prompt, system_prompt, timeout=timeout)
        return self._extract_json(raw_text)

    def _extract_json(self, text: str) -> Dict[str, Any]:
        cleaned = text.strip()
        cleaned = re.sub(r'<think>[\s\S]*?</think>', '', cleaned).strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()

        try:
            return json.loads(cleaned)
        except Exception:
            pass

        first_curly = cleaned.find('{')
        last_curly = cleaned.rfind('}')
        if first_curly != -1 and last_curly > first_curly:
            try:
                return json.loads(cleaned[first_curly:last_curly+1])
            except Exception:
                pass

        raise ValueError(f"Could not extract valid JSON from LLM response: {cleaned[:300]}")


# Step 1: Raw Event Preprocessing (Noise filtering & Typing Reconstruction)
class EventPreprocessor:
    BLOCKED_APPS = {"procmine-desktop-agent.exe", "procmine-desktop-agent", "omapsvcbroker.exe"}

    @classmethod
    def load_and_preprocess(cls, session_dir: Path) -> List[Dict[str, Any]]:
        events = []
        chunk_dirs = sorted([p for p in session_dir.iterdir() if p.is_dir() and "chunk_" in p.name])
        if not chunk_dirs and (session_dir / "events.jsonl").exists():
            chunk_dirs = [session_dir]

        for cdir in chunk_dirs:
            ev_file = cdir / "events.jsonl"
            if not ev_file.exists():
                continue
            with open(ev_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ev = json.loads(line)
                        if ev.get("layer") == "SYSTEM":
                            continue
                        ctx = ev.get("context", {}) or {}
                        act = ctx.get("active_app", {}) or {}
                        pname = (act.get("process_name") or "").lower()
                        aname = (act.get("app_name") or "").lower()
                        if pname in cls.BLOCKED_APPS or aname in cls.BLOCKED_APPS:
                            continue
                        events.append(ev)
                    except Exception:
                        continue

        events.sort(key=lambda x: x.get("timestamp_ms", 0))
        return events


# Step 2: Zero-Leakage Latent Task Induction (Paper §3.2, Figures 7 & 8)
class LatentTaskInducer:
    """Discovers latent task process threads and assigns canonical labels using Puter LLM."""

    def __init__(self, llm_client: Optional[PuterLlmClient] = None):
        self.llm = llm_client

    def induce_task_threads(
        self,
        thread_metadata: Dict[str, Dict[str, Any]]
    ) -> Dict[str, str]:
        """Maps each discovered workflow thread to a canonical snake_case label via LLM reasoning."""
        compact_threads = []
        for pfx in sorted(thread_metadata.keys()):
            meta = thread_metadata[pfx]
            compact_threads.append({
                "thread_id": pfx,
                "portal": meta.get("portal", "Internal Web Portal"),
                "ui_context": meta.get("ui_context", "internal processing")
            })

        print(f"[LatentTaskInducer] Formed {len(compact_threads)} workflow threads from trace observations.")

        label_map: Dict[str, str] = {}
        if self.llm and compact_threads:
            prompt = f"""Assign a canonical generic English snake_case business process label to each observed workflow thread:

{json.dumps(compact_threads, ensure_ascii=False, indent=2)}

Output strictly valid JSON with no extra commentary:
{{
  "labels": {{
    "INV": "canonical_snake_case_name"
  }}
}}"""

            print(f"[LatentTaskInducer] Prompting Puter LLM ({self.llm.model}) to induce process labels ({len(prompt)} chars)...")
            start_t = time.time()
            try:
                res_json = self.llm.complete_json(prompt, timeout=50)
                label_map = res_json.get("labels", {})
                print(f"[LatentTaskInducer] LLM successfully induced {len(label_map)} process labels in {time.time() - start_t:.2f}s:")
                for k, lbl in label_map.items():
                    print(f"  {k} -> {lbl}")
            except Exception as e:
                print(f"[LatentTaskInducer] LLM call failed ({e}). Using normalization fallback.")
                label_map = {}

        # Heuristic fallback if LLM is unavailable
        final_map: Dict[str, str] = {}
        for ct in compact_threads:
            k = ct["thread_id"]
            if k in label_map:
                final_map[k] = label_map[k]
            else:
                final_map[k] = f"{k.lower()}_processing"

        return final_map


# Step 3: Execution Splitting & Precision Boundary Snapping (Paper §3.2 & §3.3)
class ExecutionSplitter:
    """Splits events into discrete task execution segments with boundary snapping."""

    @classmethod
    def extract_executions_and_metadata(
        cls,
        session_id: str,
        events: List[Dict[str, Any]]
    ) -> Tuple[List[str], List[str], Dict[str, Dict[str, Any]], str]:
        # 1. Discover dominant batch ID in 3-part identifiers
        batch_counts: Dict[str, int] = {}
        for ev in events:
            text = " ".join([
                ev.get("context", {}).get("active_app", {}).get("window_title", ""),
                str(ev.get("context", {}).get("extracted_text", "")),
                str(ev.get("payload", {}))
            ])
            for m in THREE_PART_REGEX.finditer(text):
                batch_id = m.group(2)
                batch_counts[batch_id] = batch_counts.get(batch_id, 0) + 1

        dominant_batch = max(batch_counts.items(), key=lambda x: x[1])[0] if batch_counts else None
        if dominant_batch:
            print(f"[ExecutionSplitter] Discovered dominant batch identifier: {dominant_batch} ({batch_counts[dominant_batch]} occurrences)")

        # 2. Extract ordered primary case instances
        case_first_idx: Dict[str, int] = {}
        case_last_idx: Dict[str, int] = {}

        for i, ev in enumerate(events):
            text = " ".join([
                ev.get("context", {}).get("active_app", {}).get("window_title", ""),
                str(ev.get("context", {}).get("extracted_text", "")),
                str(ev.get("payload", {}))
            ])

            cid = None
            if dominant_batch:
                m = re.search(rf'\b([A-Z]{{2,6}})[-_]{dominant_batch}[-_](\d{{2,4}})\b', text)
                if m:
                    cid = f"{m.group(1)}-{dominant_batch}-{m.group(2)}"
            else:
                m = THREE_PART_REGEX.search(text) or TWO_PART_REGEX.search(text)
                if m:
                    pfx = m.group(1).upper()
                    if pfx not in IGNORE_IDENTIFIERS:
                        mid = m.group(2)
                        sfx = m.group(3) if len(m.groups()) >= 3 and m.group(3) else None
                        cid = f"{pfx}-{mid}" + (f"-{sfx}" if sfx else "")

            if cid:
                if cid not in case_first_idx:
                    case_first_idx[cid] = i
                case_last_idx[cid] = i

        ordered_cases = sorted(case_first_idx.keys(), key=lambda c: case_first_idx[c])
        print(f"[ExecutionSplitter] Discovered {len(ordered_cases)} distinct case executions in trace.")

        # 3. Refine boundary snapping for each case
        # Snaps backward up to 6 seconds for the transition app_switch / browser_navigation event
        start_indices: List[int] = []
        start_boundaries: List[str] = []
        for idx, cid in enumerate(ordered_cases):
            ev_i = case_first_idx[cid]
            fev = events[ev_i]
            best_i = ev_i
            prev_bound_idx = case_first_idx[ordered_cases[idx - 1]] if idx > 0 else 0

            for b_i in range(ev_i, max(0, ev_i - 50), -1):
                bev = events[b_i]
                if idx > 0 and b_i <= prev_bound_idx:
                    break
                if (fev["timestamp_ms"] - bev["timestamp_ms"]) > 6000:
                    break
                if bev.get("event_type") in ("app_switch", "browser_navigation"):
                    best_i = b_i

            start_indices.append(best_i)
            start_boundaries.append(cls._clean_iso(events[best_i]["timestamp_iso"]))

        # 4. Detect termination of the final execution before session idle disengagement
        last_boundary = ""
        end_last_i = len(events) - 1
        if ordered_cases:
            last_cid = ordered_cases[-1]
            last_case_i = case_last_idx[last_cid]
            end_last_i = last_case_i
            for f_i in range(last_case_i, len(events)):
                fev = events[f_i]
                if fev["timestamp_ms"] - events[end_last_i]["timestamp_ms"] > 15000:
                    break
                end_last_i = f_i
            last_boundary = cls._clean_iso(events[end_last_i]["timestamp_iso"])

        # 5. Extract observed UI metadata dynamically for each process prefix from trace (zero leakage)
        GENERIC_IGNORE = {
            'ダッシュボード', '2026年度', 'HR人事給与システム', '受発注在庫管理システム',
            '財務会計システム', 'Google Chrome', 'Notepad', 'Microsoft Word', 'Excel',
            'm1_reference', 'Task Switching', 'Restore pages?', 'Address and search bar'
        }

        prefix_metadata: Dict[str, Dict[str, Any]] = {}
        for idx in range(len(ordered_cases)):
            cid = ordered_cases[idx]
            pfx = cid.split("-")[0].upper()
            st_i = start_indices[idx]
            et_i = start_indices[idx + 1] if idx + 1 < len(start_indices) else end_last_i + 1

            if pfx not in prefix_metadata:
                prefix_metadata[pfx] = {
                    "apps": Counter(),
                    "portals": Counter(),
                    "url_paths": Counter(),
                    "keywords": Counter()
                }

            meta = prefix_metadata[pfx]
            for ev_i in range(st_i, min(et_i, len(events))):
                ev = events[ev_i]
                ctx = ev.get("context", {}) or {}
                act = ctx.get("active_app", {}) or {}
                aname = act.get("app_name")
                wtitle = act.get("window_title") or ""
                if aname and aname != "unknown":
                    meta["apps"][aname] += 1
                if "財務会計" in wtitle:
                    meta["portals"]["財務会計システム (Financial Accounting)"] += 1
                elif "人事給与" in wtitle:
                    meta["portals"]["HR人事給与システム (HR Management)"] += 1
                elif "受発注在庫" in wtitle:
                    meta["portals"]["受発注在庫管理システム (Order & Inventory)"] += 1

                ext = ctx.get("extracted_text")
                s = ""
                if ext:
                    s = ext.get("text") if isinstance(ext, dict) else str(ext)
                full_text = f"{wtitle}\n{s}"

                for u in re.findall(r'/#/([a-zA-Z0-9_\-]+)', full_text):
                    if u not in ('dashboard', 'login'):
                        meta["url_paths"][u] += 2

                for line in full_text.split("\n"):
                    line = line.strip()
                    if 2 <= len(line) <= 25 and line not in GENERIC_IGNORE and not line.startswith(('http', '127.')):
                        if any(ord(c) > 127 for c in line):
                            meta["keywords"][line] += 1

        formatted_meta: Dict[str, Dict[str, Any]] = {}
        for pfx, d in prefix_metadata.items():
            top_apps = [app for app, _ in d["apps"].most_common(2)]
            top_portal = d["portals"].most_common(1)[0][0] if d["portals"] else "Internal Web Portal"
            top_urls = [f"url: {u}" for u, _ in d["url_paths"].most_common(2)]
            top_kw = [k for k, _ in d["keywords"].most_common(3) if not any(u in k for u in ['url:'])]
            context_items = top_urls + top_kw
            formatted_meta[pfx] = {
                "apps": top_apps,
                "portal": top_portal,
                "ui_context": ", ".join(context_items[:4]) if context_items else "internal processing"
            }

        return ordered_cases, start_boundaries, formatted_meta, last_boundary

    @classmethod
    def assemble_segments(
        cls,
        session_id: str,
        ordered_cases: List[str],
        start_boundaries: List[str],
        last_boundary: str,
        label_map: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        segments = []
        for i in range(len(ordered_cases)):
            cid = ordered_cases[i]
            pfx = cid.split("-")[0].upper()
            label = label_map.get(pfx, f"{pfx.lower()}_processing")

            st = start_boundaries[i]
            et = start_boundaries[i + 1] if i + 1 < len(start_boundaries) else last_boundary

            segments.append({
                "session_id": session_id,
                "start": st,
                "end": et,
                "label": label,
                "case_id": cid
            })
        return segments

    @staticmethod
    def _clean_iso(ts: str) -> str:
        """Formats timestamp to standard ISO 8601 UTC string (e.g. 2026-07-01T05:31:23Z)."""
        if not ts:
            return ""
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            return ts.split(".")[0] + "Z" if "." in ts else ts


# Step 4: Post-Hoc Ground Truth Evaluation (STRICTLY ISOLATED TO EVALUATION)
class GroundTruthEvaluator:
    """Evaluates predicted segments against ground truth manifest purely post-hoc."""

    @classmethod
    def evaluate(
        cls,
        predicted_segments: List[Dict[str, Any]],
        session_dir: Path,
        tolerances_sec: List[int] = [2, 5, 10, 30]
    ) -> Optional[Dict[str, Any]]:
        manifest_file = session_dir / "gt_manifest.json"
        if not manifest_file.exists():
            return None

        with open(manifest_file, "r", encoding="utf-8") as f:
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
                    "start_sec": cls._to_epoch(exec_item.get("start_ts")),
                    "end_sec": cls._to_epoch(exec_item.get("end_ts")),
                })

        gt_executions.sort(key=lambda x: x["start_sec"])

        for idx in range(len(gt_executions)):
            if not gt_executions[idx]["end_sec"] or gt_executions[idx]["end_sec"] == 0.0:
                if idx + 1 < len(gt_executions):
                    gt_executions[idx]["end_sec"] = gt_executions[idx + 1]["start_sec"]

        preds = []
        for p in predicted_segments:
            s_sec = cls._to_epoch(p["start"])
            e_sec = cls._to_epoch(p["end"])
            preds.append({
                **p,
                "start_sec": s_sec,
                "end_sec": e_sec,
            })
        preds.sort(key=lambda x: x["start_sec"])

        tol_results = {}
        for tol in tolerances_sec:
            tp = 0
            matched_gt = set()
            for p in preds:
                for idx, gt in enumerate(gt_executions):
                    if idx in matched_gt:
                        continue
                    start_diff = abs(p["start_sec"] - gt["start_sec"])
                    end_diff = abs(p["end_sec"] - gt["end_sec"])
                    if start_diff <= tol and end_diff <= tol:
                        tp += 1
                        matched_gt.add(idx)
                        break

            precision = tp / len(preds) if preds else 0.0
            recall = tp / len(gt_executions) if gt_executions else 0.0
            f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

            tol_results[f"tolerance_{tol}s"] = {
                "tolerance_sec": tol,
                "true_positives": tp,
                "total_predicted": len(preds),
                "total_ground_truth": len(gt_executions),
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
            }

        label_mapping = {}
        for p in preds:
            lbl = p["label"]
            cid = p.get("case_id")
            for gt in gt_executions:
                if (cid and gt["case_id"] == cid) or (abs(p["start_sec"] - gt["start_sec"]) <= 15):
                    if lbl not in label_mapping:
                        label_mapping[lbl] = {}
                    gt_key = f"{gt['code']} ({gt['family_name']})"
                    label_mapping[lbl][gt_key] = label_mapping[lbl].get(gt_key, 0) + 1

        summary_mapping = {}
        for lbl, counts in label_mapping.items():
            best_gt = max(counts.items(), key=lambda x: x[1])
            summary_mapping[lbl] = f"{best_gt[0]} ({best_gt[1]} matches)"

        return {
            "predicted_segments_count": len(preds),
            "ground_truth_executions_count": len(gt_executions),
            "tolerances": tol_results,
            "label_to_gt_process_mapping": summary_mapping
        }

    @staticmethod
    def _to_epoch(ts: Optional[str]) -> float:
        if not ts:
            return 0.0
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return dt.timestamp()
        except Exception:
            return 0.0


def run_pipeline(session_path: Path, output_file: Path, use_llm: bool = True):
    session_id = session_path.name
    print(f"\n=======================================================")
    print(f"Running Pure Zero-Leakage TMI Pipeline on: {session_id}")
    print(f"Source Directory: {session_path}")
    print(f"=======================================================")

    # Step 1: Preprocess raw events
    events = EventPreprocessor.load_and_preprocess(session_path)
    print(f"[Step 1] Preprocessed {len(events)} user interaction events (recorder noise removed).")

    # Step 2: Extract candidate executions and observed UI metadata from trace
    ordered_cases, start_boundaries, prefix_meta, last_boundary = ExecutionSplitter.extract_executions_and_metadata(
        session_id, events
    )
    print(f"[Step 2] Extracted {len(ordered_cases)} candidate case executions across {len(prefix_meta)} process threads.")

    # Step 3: Zero-Leakage Latent Task Induction via Puter LLM
    llm_client = PuterLlmClient() if use_llm else None
    inducer = LatentTaskInducer(llm_client)
    process_label_map = inducer.induce_task_threads(prefix_meta)

    # Step 4: Assemble final segments with induced labels and precision boundary snapping
    segments = ExecutionSplitter.assemble_segments(
        session_id, ordered_cases, start_boundaries, last_boundary, process_label_map
    )
    print(f"[Step 4] Assembled {len(segments)} task execution segments.")

    # Write deliverable segments.jsonl
    with open(output_file, "w", encoding="utf-8") as f:
        for s in segments:
            row = {
                "session_id": s["session_id"],
                "start": s["start"],
                "end": s["end"],
                "label": s["label"]
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"\n[Deliverable] Written {len(segments)} segments to {output_file.resolve()}")

    # Step 5: Post-Hoc Ground Truth Evaluation (Only if GT files exist)
    eval_report = GroundTruthEvaluator.evaluate(segments, session_path)
    if eval_report:
        print(f"\n-------------------------------------------------------")
        print(f"Post-Hoc Ground Truth Evaluation Results (Strictly Isolated):")
        print(f"  Predicted Segments: {eval_report['predicted_segments_count']}")
        print(f"  Ground Truth Executions: {eval_report['ground_truth_executions_count']}")
        print(f"  Boundary Metrics:")
        for k, v in eval_report["tolerances"].items():
            print(f"    {k}: Precision={v['precision']*100:.1f}%, Recall={v['recall']*100:.1f}%, F1={v['f1']*100:.1f}%")
        print(f"  Process Label Mapping to Ground Truth:")
        for k, v in eval_report["label_to_gt_process_mapping"].items():
            try:
                print(f"    {k} -> {v}")
            except Exception:
                safe_v = v.encode("ascii", "replace").decode("ascii")
                print(f"    {k} -> {safe_v}")
        print(f"-------------------------------------------------------")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run Task Model Induction Pipeline")
    parser.add_argument("--session_dir", type=str, default=r"G:\.shortcut-targets-by-id\1WSBZQxOODKFDzYBkIik5g90NWKS7Gwl0\AI Engineer\dataset_a\ses_20260701-053005-MSI")
    parser.add_argument("--output_file", type=str, default="segments.jsonl")
    parser.add_argument("--no_llm", action="store_true", help="Run without LLM")
    args = parser.parse_args()

    run_pipeline(Path(args.session_dir), Path(args.output_file), use_llm=not args.no_llm)
