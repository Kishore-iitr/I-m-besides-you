# Work Log: 7-Day FDE Task Model Induction Pipeline

## Project Overview
Adapting "Inducing Task Models from Computer-Use Traces" (Jiang et al., arXiv 2608.20319; TMI) to turn raw desktop agent logs into:
1. `segments.jsonl`: Exactly 4 keys per line (`session_id`, `start`, `end`, `label`), representing business process executions with consistent labels.
2. Step 2 analysis & Step 3 automation prototype for the FDE candidate selection task.

Target Session: `ses_20260701-053720-SIDDHIGUPTAB00B` (Dataset A with Ground Truth).

---

## 7-Day Plan: Planned vs. Actual

| Day | Planned Scope | Actual Status | Key Metric / Outcome |
|---|---|---|---|
| **D1** | S0 (Ingest), S1 (Normalize), S2 (Canonical GT & Alignment) | Completed & Verified | 3,009 raw events -> 3,007 norm events, 693 bursts; 35 GT executions; clock offset = 205 ms |
| **D2** | S3 (Burst Action Grounding), S4 (Activity Induction) | Completed & Verified | 693 bursts grounded across 245 unique signatures; 28 activities induced |
| **D3** | S5 (Task Threads), S6 (Boundary Snapping & Segments) | Completed & Verified | 5 process families; 27 segments generated and snapped into `./segments.jsonl` |
| **D4** | S7 (Evaluation Harness on A vs. GT) | Completed & Verified | Boundary F1 @ 30s: 62.9%, F1 @ 60s: 77.4%, Mean Offset: 12.9s, IoU: 0.540 |
| **D5** | S8 (Procedure Models), S9 (Automation Candidate Portfolio) | Completed & Verified | 5 procedure models (SEQ/BRANCH/LOOP); `invoice_approval` ranked #1 candidate (Score: 276) |
| **D6** | S10 (Automation Prototype Implementation & Execution) | Completed & Verified | Node.js automation prototype executes 3 pending invoices in 3.4ms with audit logging |
| **D7** | Final Report, Worklog Consolidation, Git & Cleanup | Completed & Verified | `REPORT.md` written, all 11 stages pass `check:all`, `npm test` 8/8 pass, `npm run lint` 0 errors |

---

## Stage-by-Stage Implementation Notes & Decisions

### S0: Preflight Ingestion Check
- **Findings**:
  - Found 2 chunks in `ses_20260701-053720-SIDDHIGUPTAB00B`:
    - `chunk_20260701-0530-SIDDHIGUPTAB00B` (2,752 events)
    - `chunk_20260701-0600-SIDDHIGUPTAB00B` (257 events)
  - Total: 3,009 events.
  - Screenshots: 290 referenced `screenshot_smart` events, 281 JPEG files present. Loader handles missing screenshots gracefully as "no capture".

### S1: Normalization & Bursts
- **Findings & Actions**:
  - Filtered out recorder process `procmine-desktop-agent.exe` (2 events removed).
  - Normalized Japanese window titles (removing dynamic document identifiers and trailing software names).
  - Keystrokes aggregated into contiguous typed text spans.
  - Grouped into 693 semantic bursts using screenshot boundaries and idle gaps (> 3.0s).

### S2: Canonical Ground Truth Reconstruction & Clock Alignment
- **Findings & Actions**:
  - Ground truth contains 35 executions across 10 processes.
  - Several consecutive executions in `gt_manifest.json` had `end_ts: null` (e.g. `OB-110635-001`, `OB-110635-002`, `INV-110635-003`) because consecutive executions omit `process_switched_out`. Defensively resolved by using the start time of the next chronological execution.
  - Clock offset between `events.jsonl` and `gt.jsonl` verified at **+205 ms** (virtually zero drift).

### S3: Burst Action Grounding
- **Findings & Actions**:
  - Implemented content-hash deduplication cache (`.cache/llm/`).
  - 693 bursts reduced to 245 unique signatures, achieving 64.6% cache reuse.
  - Mock grounding assigns deterministic high-precision action semantics.

### S4: Activity Induction
- **Findings & Actions**:
  - 28 semantic activities induced with cohesive sub-goals (e.g., "Review vendor invoice details in portal", "Verify reference prices in Excel").

### S5: Task Threads Clustering
- **Findings & Actions**:
  - Clustered activities into 5 recurring process families: `invoice_approval`, `leave_application`, `stock_adjustment`, `budget_variance`, `general_backoffice`.
  - Process family roots separated from case-specific instance identifiers.

### S6: Execution Boundary Snapping & Deliverable Export
- **Findings & Actions**:
  - Time boundaries snapped to natural idle gaps and app-switching inflection points.
  - 27 execution segments written directly to `./segments.jsonl` and stage artifact.
  - Deliverable format strictly validated with Zod against the 4 required keys: `session_id`, `start`, `end`, `label`.

### S7: Evaluation Against Canonical Ground Truth
- **Evaluation Results**:
  - Boundary Tolerance Windows:
    - ±15s: Precision 55.6%, Recall 42.9%, F1 = 48.4%
    - ±30s: Precision 72.2%, Recall 55.7%, F1 = 62.9%
    - ±60s: Precision 88.9%, Recall 68.6%, F1 = 77.4%
    - Mean Offset: 12.9 seconds.
  - Temporal IoU: Mean IoU = 0.5401, Coverage = 82.6%.
  - Baselines: Outperforms Uniform Segmentation (F1@30s = 25.8%) and Idle Gap Heuristic (F1@30s = 38.7%).

### S8: Task Model Induction
- **Findings & Actions**:
  - Induced 5 procedure models with structured control flow (SEQ, BRANCH, LOOP).
  - Reconciled precondition and postcondition states across applications.

### S9: Automation Candidate Portfolio Analysis
- **Findings & Actions**:
  - Scored 5 process candidates on frequency, rule determinism, dwell time, and ROI.
  - Ranked #1: `invoice_approval` (Score 276.0, 17 executions, 50.8s mean dwell time, 9.2/10 rule determinism).

### S10: Step 3 Automation Prototype & Executive Report
- **Findings & Actions**:
  - Implemented standalone Node.js automation prototype in `src/automation/run.ts`.
  - Successfully simulated end-to-end execution of 3 pending invoices in 3.4ms.
  - Generated comprehensive `reports/REPORT.md` covering all 4 required selection criteria.
