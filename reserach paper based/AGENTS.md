# AGENTS.md — TMI Pipeline Specification & Principles

## 0.1 Goal
Build a TypeScript/Node pipeline that turns raw desktop-agent operation logs into:
(a) `segments.jsonl` — one line per execution of a business process, with consistent labels across sessions.
(b) The analysis and automation prototype for an FDE intern selection task.

### Deliverable line format (exactly these four keys, nothing else in segments.jsonl):
```json
{"session_id":"ses_...","start":"2026-07-01T18:32:32Z","end":"2026-07-01T18:35:41Z","label":"returns_processing"}
```

Scoring: correctness of boundaries between units of work, and whether the same process always gets the same label. Label text is not scored.

## 0.2 Data
- Layout: `dataset_x/ses_<date>-<time>-<machine>/chunk_*/{events.jsonl, manifest.json, screenshots/*.jpg}`
- Dataset A sessions also have `gt.jsonl` and `gt_manifest.json`.
- The loader must never assume a chunk has events, a manifest, or a matching name.
- Missing image = "no capture", never an error.
- Keystrokes are the only reliable source of typed text.
- Filter out recorder's own process (`procmine-desktop-agent.exe`).
- Build canonical GT defensively (handle duplicate starts, unpaired switches).

## 0.3 Non-negotiable design principles
1. Staged and checkable: Artifacts stored under `artifacts/<dataset>/<session>/`. Each stage has `npm run sN` and `npm run check:sN`. Idempotent and resumable.
2. Mock-first: Runs end-to-end with `--mock`. `npm run demo:mock` runs S0–S10.
3. Degrade gracefully: Three input modes (events+screens, events-only, screens-only).
4. Dataset shift: No A-specific constants in code. Config files `config/dataset_a.json` and `config/dataset_b.json`.
5. LLM discipline: Provider-agnostic adapter, zod validation, repair retry, content-hash cache, usage log, token/cost budgets.
6. Privacy: Support `REDACT=true` option.
7. Evidence, not vibes: Every number reproducible by command.
8. Git: Commit at end of every stage with message `S<N>: <summary> | <key metric>`, tag `stage-N-pass`.

## 0.4 TMI Adaptations
A. Unit of output: Time segments per execution with deterministic boundary snapping.
B. Root = process family, not one-off deliverable. Distinct case IDs do NOT create separate roots.
C. Cross-session label consistency: Global canonicalization pass over per-session roots.
D. Cost: Ground bursts (events between screenshots/idle gaps), not raw events.
E. Missing data: Handle missing screenshots/events gracefully.
F. Noise: Allow unrelated activity to remain unassigned (`UNRELATED` root).
G. Evaluation: Rigorous evaluation harness for A (Precision, Recall, F1 @ tolerance, ARI, NMI).
