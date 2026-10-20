# Patch to TMI_PIPELINE_BUILD_SPEC.md — Puter + OpenRouter ":free" models as the LLM backend

How to use: paste this to the coding agent right after S0 passes (before S3). Tell it: "Apply this patch. Where it conflicts with the earlier spec, this patch wins. Do not start S3 until S0.5 passes."

What changed and why: the original spec assumed a paid multimodal API with a dollar budget. Free OpenRouter models differ in four ways that matter here: (1) few accept images, (2) request rate is limited, (3) they are weaker at long structured-JSON tasks, (4) the free lineup changes over time. Everything below is about surviving those four.

Facts this patch relies on (from Puter's public docs, not tested by me — S0.5 verifies each one against your account):
- Puter.js runs in Node: `import { init } from "@heyputer/puter.js/src/init.cjs"; const puter = init(process.env.PUTER_AUTH_TOKEN); const r = await puter.ai.chat(prompt, { model })`, answer in `r.message.content`. (Puter "Node.js quick start".)
- Puter also exposes an OpenAI-compatible endpoint, base URL `https://api.puter.com/puterai/openai/v1/`, with the Puter auth token as the API key (copy it from puter.com/dashboard). Free OpenRouter models appear there with ids like `inclusionai/ling-2.6-flash:free`.
- A third-party gateway README claims free Puter accounts use a different "user-pays driver" path and that the first-party OpenAI-compatible endpoint is for paid accounts. That conflicts with Puter's own tutorials, so **do not assume either transport works — probe both.**
- OpenRouter's own free tier is documented as 20 requests/minute and 1,000 requests/day. Puter's marketing says no daily cap because each user pays through their own account. Treat the stricter numbers as real until the probe and your Puter usage dashboard show otherwise.
- Puter documents an OCR call (`puter.ai.img2txt`) and, per a Puter GitHub issue, `puter.ai.chat` accepts `response_format` and image data URLs for some models. Support is per model; probe it.

---

## A. Replace the LLM-adapter requirements (spec §0.3 item 5 and §0.5)

1. Provider `puter` is the default. Two transports behind one interface, chosen by `PUTER_TRANSPORT=auto|sdk|openai` (`auto` = whichever passes the S0.5 probe, preferring `sdk`).
2. `.env.example`:
```
LLM_PROVIDER=puter
PUTER_AUTH_TOKEN=            # never commit; .env is gitignored; preflight refuses to run if empty
PUTER_TRANSPORT=auto
GROUNDING_MODEL=             # vision-capable free model if one passes the probe, else text-only
REASONING_MODEL=
JUDGE_MODEL=
FALLBACK_MODELS=             # comma-separated, tried in order on repeated failure
RPM_LIMIT=15                 # stay under 20 rpm
DAILY_CALL_CAP=900           # stay under 1000/day until proven otherwise
MAX_PROMPT_TOKENS=12000      # free models vary; keep prompts modest
TEMPERATURE=0.2
CONCURRENCY=2
```
3. Model ids: accept the id exactly as the user writes it. If the call fails with unknown-model, retry once with/without an `openrouter:` prefix, then print the 5 closest ids from the live catalog and stop. Never silently substitute a different model.
4. Replace the dollar budget (`MAX_USD`) with call budgets: `RPM_LIMIT`, `DAILY_CALL_CAP`, and a persistent counter in `.cache/usage_day.json` (resets at UTC midnight). When the cap is hit the run **checkpoints and exits cleanly**; rerun resumes from the cache.
5. Reliability: exponential backoff with jitter, honour `Retry-After`, treat 429 as normal; circuit breaker after N consecutive failures → next model in `FALLBACK_MODELS` → otherwise exit with a resumable state.
6. JSON handling: do **not** rely on `response_format`. Strip code fences and any `<think>…</think>` block, extract the first balanced JSON object, validate with zod, one repair retry that shows the validation error, then fall back to the deterministic rule for that stage.
7. Reproducibility: the cache key includes `model_id`, prompt version, temperature and the prompt hash. Every artifact file gets a `_meta.json` recording model ids used, transport, date, and call counts. Free models get rotated or retired; if a model disappears mid-project the report must say which outputs came from which model.
8. `npm run estimate` now prints, per stage and for (A-dev 5 sessions / A-full / B): number of calls, and days needed at `DAILY_CALL_CAP`. Run it before every large run.

## B. Insert stage S0.5 — LLM probe and model selection (no pipeline code needed yet)

Commands: `npm run llm:models`, `npm run llm:probe -- --model <id>`, `npm run check:llm`.

1. `llm:models`: list the live catalog (try the SDK's model-listing if it exists; otherwise `https://api.puter.com/puterai/chat/models` — verify this URL, it came from a third-party README). Filter to `:free` ids; print id, context length and input modalities if the catalog exposes them.
2. `llm:probe` runs on a candidate model and records, in `reports/llm_probe.md`:
   - (a) Basic call works on **both** transports.
   - (b) Structured JSON: 20 trials with a small schema; % valid before repair and after repair.
   - (c) Japanese: feed 10 real `context.extracted_text` samples from Dataset A and ask for case/order identifiers and company names; score against a regex-built answer key.
   - (d) Vision: send 5 real A screenshots; ask for the visible case id and the screen title; does the model accept images at all, and how accurate is it?
   - (e) Throughput: 25 calls in a burst; count 429s, latency p50/p95, and whether a daily counter appears to exist.
   - (f) Long context: place a known identifier in an 8k-token and a 16k-token prompt and ask for it back.
3. Model selection rule written into the report: `GROUNDING_MODEL` = best model passing (b),(c),(d); if none passes (d), set `GROUNDING_MODE=ocr_text` (see §C). `REASONING_MODEL` = best passing (b),(c),(f). Record the second-best as a fallback.
4. `check:llm` passes only if at least one model passes (b) with ≥ 90% valid-after-repair **and** (c) with ≥ 80%. If nothing passes, tell me and stop: the pipeline will run in `--llm off` rule-heavy mode until a model is found.

## C. Changes to the pipeline stages

**S3 grounding — two paths, picked by the probe**
- `vision` path: as in the original spec, if a free vision-capable model passed (d).
- `ocr_text` path (likely default with free models): OCR each frame (Puter's OCR call or local `tesseract.js` with the Japanese language data — implement one, keep the other as option), then a text-only model grounds the burst from OCR text + event summary + `extracted_text`. **Validate the OCR for free:** wherever both OCR text and `context.extracted_text` exist for the same moment (≈4–5% of events in the sample), compute character-level similarity and report it in `check:s3`. If Japanese OCR quality is poor (report the number), say so and lean more on events, titles and `extracted_text`.
- Cut calls: (1) **batch** 5–8 bursts per call in text-only mode; (2) **dedupe** bursts by a signature (normalized event classes + title template + OCR/extracted-text hash) and ground each signature once; (3) skip the LLM for trivial bursts (pure app-switch flicker, idle) and label them by rule.
- Always store `grounding_mode` per burst.

**Rule-based safety net everywhere.** Every LLM stage already has a deterministic fallback; make `--llm off` a first-class flag that produces a full `segments.jsonl` from rules alone (case-id change + title-template/app change + idle gaps + clustering of burst signatures with TF-IDF/char n-grams). Report on A: rules-only vs LLM-assisted, so the final report can justify what the LLM actually adds. This is also the insurance if the free tier throttles you on submission day.

**S4** — smaller batches (≈20 bursts), shorter prior-context, stricter validators; on repeated validator failure use the rule split for that batch and log it.

**S5 global canonicalization** — do not depend on an embedding API (free chat models may not offer one). Cluster per-session roots with char n-gram TF-IDF over `label + summary + family_anchors`, and use the LLM only to confirm merges for ambiguous pairs.

**S7** — self-consistency needs repeated runs; with call caps do 2 runs on B (or 3 on a sampled subset) and say so. Prefer deterministic stages' stability numbers when LLM budget is short.

**S8** — input ≤ 3 executions per family, simpler schemas. If time is short, drop the objective tree and keep the procedure model (the automation spec needs procedures, not goal hierarchies).

**Experiment size.** Run the LLM stages on a subset of A first (e.g. 8 dev + 4 test sessions) and extend only if the call budget allows; report which sessions were used. Run all 15 B sessions. Re-run `estimate` after S3 so the plan is based on measured calls per session, not guesses.

## D. Risks specific to this backend (add to PART 4)

1. **Vision availability** — free models may not read screenshots; the grounding quality ceiling then depends on Japanese OCR. Evidence to collect: probe (d) and the OCR-vs-`extracted_text` score.
2. **Rate and daily caps** — 15 rpm × 60 × 24 = 21,600 calls theoretical, but a 900/day cap means a 4,000-call grounding pass takes ≥ 4–5 days. Mitigation: batching, dedupe, subset of A, resumable cache.
3. **Model churn** — free ids can disappear; record ids per artifact; keep `FALLBACK_MODELS`.
4. **Quality on long JSON** — small free models drift; validators + repair + rule fallback.
5. **Data handling** — prompts and screenshots pass through Puter and then OpenRouter and the upstream provider; free endpoints may have different retention/training terms (I have not verified them). Check OpenRouter's data-policy settings for free models and the task's rules; the data is described as a test environment, but redact anyway if in doubt (`REDACT=true`).
6. **Account billing** — "user-pays" means usage may land on your Puter account; watch the usage dashboard during the first large run.
7. **Single provider dependency** — Puter outage stalls the pipeline; the cache and `--llm off` mode are the mitigations.

## E. Updated plan impact (record in WORKLOG)
D1 S0 + S0.5 + S1–S2 · D2 S3 on 3 sessions, measure calls/session, decide batching · D3 S3–S4 on A subset · D4 S5–S6 on A subset + first metrics · D5 hardening + B run · D6 S8–S9 · D7 S10 + report. If call caps bite, S10 shrinks to the single best candidate and the report says why.
