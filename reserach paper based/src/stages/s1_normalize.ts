import path from 'node:path';
import fs from 'node:fs';
import { DatasetName, NormalizedEvent, Burst, TypedText, Identifier } from '../types.js';
import { loadDatasetConfig } from '../config.js';
import { inspectSession, loadAllRawEvents, listSessions } from '../io/loader.js';
import { buildFrameList } from '../io/screenshots.js';
import { writeJSONL } from '../io/jsonl.js';
import { normalizeRawEvents } from '../norm/events.js';
import { reconstructKeystrokes } from '../norm/keystrokes.js';
import { extractGenericIdentifiers, RawTextSource } from '../norm/ids.js';
import { formBursts } from '../norm/bursts.js';
import { NormalizedEventSchema, BurstSchema, TypedTextSchema, IdentifierSchema } from '../schemas/norm.js';

export interface S1SessionStats {
  sessionId: string;
  dataset: DatasetName;
  rawEventsCount: number;
  normalizedCount: number;
  burstsCount: number;
  eventCoveragePct: number;
  medianEventsPerBurst: number;
  p95EventsPerBurst: number;
  pctWithBothFrames: number;
  pctWithExtractedText: number;
  identifiersTotal: number;
  identifiersByKind: Record<string, number>;
  typedTextsCount: number;
}

export async function processSessionS1(
  sessionId: string,
  dataset: DatasetName,
  projectRoot: string = process.cwd(),
  limit?: number
): Promise<S1SessionStats> {
  const config = loadDatasetConfig(dataset, projectRoot);
  const sessionInfo = inspectSession(sessionId, dataset, projectRoot);
  const rawEvents = await loadAllRawEvents(sessionInfo, limit);

  // 1. Normalize events (filters recorder and noise system events)
  const normalizedEvents = normalizeRawEvents(rawEvents, config);

  // Validate normalized events with Zod
  for (const ev of normalizedEvents) {
    NormalizedEventSchema.parse(ev);
  }

  // 2. Reconstruct typed text runs
  const typedTexts = reconstructKeystrokes(rawEvents, config.keystroke_idle_threshold_ms || 1500);
  for (const tt of typedTexts) {
    TypedTextSchema.parse(tt);
  }

  // 3. Discover generic identifiers
  const textSources: RawTextSource[] = [];
  for (const ev of rawEvents) {
    if (ev.context?.extracted_text?.text) {
      textSources.push({
        text: ev.context.extracted_text.text,
        source: 'extracted_text',
        timestamp_ms: ev.timestamp_ms,
      });
    }
    const title = ev.context?.active_app?.window_title || ev.payload?.window_title;
    if (title) {
      textSources.push({
        text: title,
        source: 'window_title',
        timestamp_ms: ev.timestamp_ms,
      });
    }
  }
  for (const tt of typedTexts) {
    textSources.push({
      text: tt.text,
      source: 'typed_text',
      timestamp_ms: tt.ts_start,
    });
  }

  const identifiers = extractGenericIdentifiers(textSources);
  for (const id of identifiers) {
    IdentifierSchema.parse(id);
  }

  // 4. Build frame list
  const frames = buildFrameList(sessionInfo, rawEvents);

  // 5. Form bursts
  const bursts = formBursts(normalizedEvents, config, frames, typedTexts);

  // Validate bursts with Zod
  for (const b of bursts) {
    BurstSchema.parse(b);
  }

  // Coverage check: sum of event_count across all event bursts must equal normalizedEvents.length
  const coveredEventCount = bursts.reduce((acc, b) => acc + b.event_count, 0);
  const coveragePct = normalizedEvents.length > 0
    ? Number(((coveredEventCount / normalizedEvents.length) * 100).toFixed(1))
    : 100;

  // Stats: median and p95 events per burst
  const eventCounts = bursts.map(b => b.event_count).sort((a, b) => a - b);
  const medianEvents = eventCounts.length > 0
    ? eventCounts[Math.floor(eventCounts.length * 0.5)]
    : 0;
  const p95Events = eventCounts.length > 0
    ? eventCounts[Math.floor(eventCounts.length * 0.95)]
    : 0;

  const withBothFrames = bursts.filter(b => b.before_frame && b.after_frame).length;
  const pctWithBothFrames = bursts.length > 0
    ? Number(((withBothFrames / bursts.length) * 100).toFixed(1))
    : 0;

  const withExtracted = bursts.filter(b => b.extracted_text && b.extracted_text.length > 0).length;
  const pctWithExtracted = bursts.length > 0
    ? Number(((withExtracted / bursts.length) * 100).toFixed(1))
    : 0;

  const idByKind: Record<string, number> = {};
  for (const id of identifiers) {
    idByKind[id.kind] = (idByKind[id.kind] || 0) + 1;
  }

  // Write stage artifacts
  const artifactsDir = path.join(projectRoot, 'artifacts', dataset, sessionId);
  if (!fs.existsSync(artifactsDir)) {
    fs.mkdirSync(artifactsDir, { recursive: true });
  }

  // Deliverables required by prompt
  await writeJSONL(path.join(artifactsDir, 'norm_events.jsonl'), normalizedEvents);
  await writeJSONL(path.join(artifactsDir, 'typed_text.jsonl'), typedTexts);
  await writeJSONL(path.join(artifactsDir, 'identifiers.jsonl'), identifiers);
  await writeJSONL(path.join(artifactsDir, 'bursts.jsonl'), bursts);

  // Backward-compatible artifact aliases
  await writeJSONL(path.join(artifactsDir, 's1_normalized.jsonl'), normalizedEvents);
  await writeJSONL(path.join(artifactsDir, 's1_bursts.jsonl'), bursts);

  return {
    sessionId,
    dataset,
    rawEventsCount: rawEvents.length,
    normalizedCount: normalizedEvents.length,
    burstsCount: bursts.length,
    eventCoveragePct: coveragePct,
    medianEventsPerBurst: medianEvents,
    p95EventsPerBurst: p95Events,
    pctWithBothFrames,
    pctWithExtractedText: pctWithExtracted,
    identifiersTotal: identifiers.length,
    identifiersByKind: idByKind,
    typedTextsCount: typedTexts.length,
  };
}

export async function runS1Normalize(
  targetSessionId?: string,
  targetDataset: DatasetName = 'A',
  projectRoot: string = process.cwd(),
  limit?: number
): Promise<{
  sessionsProcessed: number;
  totalNormalized: number;
  totalBursts: number;
  sessionStats: S1SessionStats[];
}> {
  const sessionsToProcess = targetSessionId
    ? [targetSessionId]
    : listSessions(targetDataset, projectRoot);

  if (sessionsToProcess.length === 0) {
    throw new Error(`No sessions found for dataset ${targetDataset}`);
  }

  const sessionStats: S1SessionStats[] = [];
  let totalNormalized = 0;
  let totalBursts = 0;

  for (const sesId of sessionsToProcess) {
    const stats = await processSessionS1(sesId, targetDataset, projectRoot, limit);
    sessionStats.push(stats);
    totalNormalized += stats.normalizedCount;
    totalBursts += stats.burstsCount;
  }

  return {
    sessionsProcessed: sessionStats.length,
    totalNormalized,
    totalBursts,
    sessionStats,
  };
}
