import fs from 'node:fs';
import path from 'node:path';
import { DatasetName, RawEvent, Frame, ModeRegion } from '../types.js';
import { inspectSession, loadAllRawEventsWithStats, listSessions } from '../io/loader.js';
import { buildFrameList } from '../io/screenshots.js';
import { writeJSONAtomic } from '../io/jsonl.js';
import {
  SessionTimeline,
  SessionTimelineSchema,
  SessionInventorySummary,
  DatasetInventory,
  DatasetInventorySchema,
  PreflightReport,
  PreflightReportSchema,
} from '../schemas/preflight.js';

/**
 * Deterministically partition [tMin, tMax] into contiguous mode regions:
 * 'events+screens' | 'events-only' | 'screens-only'
 * ensuring sum(duration_seconds) equals (tMax - tMin) / 1000.
 */
export function computeModeRegions(
  tMin: number,
  tMax: number,
  events: RawEvent[],
  frames: Frame[],
  eventGapThresholdMs: number = 30000,
  frameProximityMs: number = 20000
): ModeRegion[] {
  if (tMax <= tMin) {
    return [];
  }

  // Identify all event-covered intervals vs gaps
  // An event gap is any interval between events > eventGapThresholdMs,
  // or the interval before the first event [tMin, firstEvent],
  // or the interval after the last event [lastEvent, tMax].
  interface TimeInterval {
    start_ms: number;
    end_ms: number;
    hasEvents: boolean;
  }

  const rawIntervals: TimeInterval[] = [];

  if (events.length === 0) {
    rawIntervals.push({ start_ms: tMin, end_ms: tMax, hasEvents: false });
  } else {
    const firstEventMs = events[0].timestamp_ms;
    const lastEventMs = events[events.length - 1].timestamp_ms;

    if (firstEventMs > tMin) {
      rawIntervals.push({ start_ms: tMin, end_ms: firstEventMs, hasEvents: false });
    }

    let curStart = firstEventMs;
    for (let i = 0; i < events.length - 1; i++) {
      const eCur = events[i];
      const eNext = events[i + 1];
      const diff = eNext.timestamp_ms - eCur.timestamp_ms;

      if (diff > eventGapThresholdMs) {
        // Close event interval at eCur
        rawIntervals.push({ start_ms: curStart, end_ms: eCur.timestamp_ms, hasEvents: true });
        // Add gap interval
        rawIntervals.push({ start_ms: eCur.timestamp_ms, end_ms: eNext.timestamp_ms, hasEvents: false });
        curStart = eNext.timestamp_ms;
      }
    }

    rawIntervals.push({ start_ms: curStart, end_ms: lastEventMs, hasEvents: true });

    if (lastEventMs < tMax) {
      rawIntervals.push({ start_ms: lastEventMs, end_ms: tMax, hasEvents: false });
    }
  }

  // Determine mode for each interval
  const candidateRegions: ModeRegion[] = [];

  for (const interval of rawIntervals) {
    if (interval.end_ms <= interval.start_ms) continue;

    // Count events in interval
    const intervalEvents = events.filter(
      e => e.timestamp_ms >= interval.start_ms && e.timestamp_ms <= interval.end_ms
    );
    // Count frames in interval (with small boundary proximity)
    const intervalFrames = frames.filter(
      f => f.timestamp_ms >= interval.start_ms - frameProximityMs &&
           f.timestamp_ms <= interval.end_ms + frameProximityMs
    );

    let mode: 'events+screens' | 'events-only' | 'screens-only';
    if (!interval.hasEvents || intervalEvents.length === 0) {
      // Gap with frames = screens-only; gap with no frames = screens-only (idle no-capture)
      mode = 'screens-only';
    } else {
      if (intervalFrames.length > 0) {
        mode = 'events+screens';
      } else {
        mode = 'events-only';
      }
    }

    const durSec = Number(((interval.end_ms - interval.start_ms) / 1000).toFixed(3));
    candidateRegions.push({
      mode,
      start_ms: interval.start_ms,
      end_ms: interval.end_ms,
      start_iso: new Date(interval.start_ms).toISOString(),
      end_iso: new Date(interval.end_ms).toISOString(),
      duration_seconds: durSec,
      events_count: intervalEvents.length,
      frames_count: intervalFrames.length,
    });
  }

  // Merge consecutive regions with the same mode to avoid fragmentation
  const mergedRegions: ModeRegion[] = [];
  for (const reg of candidateRegions) {
    if (mergedRegions.length === 0) {
      mergedRegions.push({ ...reg });
    } else {
      const last = mergedRegions[mergedRegions.length - 1];
      if (last.mode === reg.mode) {
        last.end_ms = reg.end_ms;
        last.end_iso = reg.end_iso;
        last.duration_seconds = Number(((last.end_ms - last.start_ms) / 1000).toFixed(3));
        last.events_count += reg.events_count;
        last.frames_count += reg.frames_count;
      } else {
        mergedRegions.push({ ...reg });
      }
    }
  }

  // Exact sanity check: ensure no gap and boundaries span exactly tMin to tMax
  if (mergedRegions.length > 0) {
    mergedRegions[0].start_ms = tMin;
    mergedRegions[0].start_iso = new Date(tMin).toISOString();
    mergedRegions[mergedRegions.length - 1].end_ms = tMax;
    mergedRegions[mergedRegions.length - 1].end_iso = new Date(tMax).toISOString();

    for (let i = 0; i < mergedRegions.length - 1; i++) {
      mergedRegions[i].end_ms = mergedRegions[i + 1].start_ms;
      mergedRegions[i].end_iso = mergedRegions[i + 1].start_iso;
      mergedRegions[i].duration_seconds = Number(
        ((mergedRegions[i].end_ms - mergedRegions[i].start_ms) / 1000).toFixed(3)
      );
    }
    const lastIdx = mergedRegions.length - 1;
    mergedRegions[lastIdx].duration_seconds = Number(
      ((mergedRegions[lastIdx].end_ms - mergedRegions[lastIdx].start_ms) / 1000).toFixed(3)
    );
  }

  return mergedRegions;
}

export async function processSessionS0(
  sessionId: string,
  dataset: DatasetName,
  projectRoot: string = process.cwd(),
  limit?: number
): Promise<{ timeline: SessionTimeline; summary: SessionInventorySummary }> {
  const sessionInfo = inspectSession(sessionId, dataset, projectRoot);
  const { events: rawEvents, malformedLinesCount } = await loadAllRawEventsWithStats(
    sessionInfo,
    limit
  );
  sessionInfo.malformedLinesCount = malformedLinesCount;

  // Build unified frame list
  const frames = buildFrameList(sessionInfo, rawEvents);

  // Time span calculation
  let tMin = Infinity;
  let tMax = -Infinity;

  if (rawEvents.length > 0) {
    tMin = Math.min(tMin, rawEvents[0].timestamp_ms);
    tMax = Math.max(tMax, rawEvents[rawEvents.length - 1].timestamp_ms);
  }
  if (frames.length > 0) {
    tMin = Math.min(tMin, frames[0].timestamp_ms);
    tMax = Math.max(tMax, frames[frames.length - 1].timestamp_ms);
  }

  if (tMin === Infinity || tMax === -Infinity || tMax < tMin) {
    tMin = 0;
    tMax = 0;
  }

  const durationSeconds = Number(((tMax - tMin) / 1000).toFixed(3));
  const eventsPerMin = durationSeconds > 0
    ? Number(((rawEvents.length / durationSeconds) * 60).toFixed(2))
    : 0;

  // Gaps over 30s
  const gapsOver30s: Array<{ start_ms: number; end_ms: number; duration_seconds: number }> = [];
  for (let i = 0; i < rawEvents.length - 1; i++) {
    const diffMs = rawEvents[i + 1].timestamp_ms - rawEvents[i].timestamp_ms;
    if (diffMs > 30000) {
      gapsOver30s.push({
        start_ms: rawEvents[i].timestamp_ms,
        end_ms: rawEvents[i + 1].timestamp_ms,
        duration_seconds: Number((diffMs / 1000).toFixed(3)),
      });
    }
  }

  // Partition into mode regions summing to durationSeconds
  const regions = computeModeRegions(tMin, tMax, rawEvents, frames, 30000, 20000);

  // Aggregations
  const eventTypes: Record<string, number> = {};
  const layers: Record<string, number> = {};
  const apps: Record<string, number> = {};
  const users = new Set<string>();
  const machines = new Set<string>();
  let screenshotsReferenced = 0;
  let screenshotsPresent = 0;

  for (const ev of rawEvents) {
    eventTypes[ev.event_type] = (eventTypes[ev.event_type] || 0) + 1;
    layers[ev.layer] = (layers[ev.layer] || 0) + 1;

    const proc = (
      ev.context?.active_app?.process_name ||
      ev.payload?.new_app?.process_name ||
      'unknown'
    ).toLowerCase();
    apps[proc] = (apps[proc] || 0) + 1;

    if (ev.source?.username_hash) users.add(ev.source.username_hash);
    if (ev.source?.machine_id) machines.add(ev.source.machine_id);

    if (ev.event_type === 'screenshot_smart') {
      screenshotsReferenced++;
    }
  }

  for (const fr of frames) {
    if (fr.exists) {
      screenshotsPresent++;
    }
  }

  let screensOnlySec = 0;
  let eventsOnlySec = 0;
  let bothSec = 0;

  for (const reg of regions) {
    if (reg.mode === 'screens-only') screensOnlySec += reg.duration_seconds;
    else if (reg.mode === 'events-only') eventsOnlySec += reg.duration_seconds;
    else if (reg.mode === 'events+screens') bothSec += reg.duration_seconds;
  }

  let primaryMode: 'events+screens' | 'events-only' | 'screens-only' = 'events+screens';
  if (bothSec >= screensOnlySec && bothSec >= eventsOnlySec) {
    primaryMode = 'events+screens';
  } else if (screensOnlySec > bothSec && screensOnlySec > eventsOnlySec) {
    primaryMode = 'screens-only';
  } else {
    primaryMode = 'events-only';
  }

  const topApp = Object.entries(apps).sort((a, b) => b[1] - a[1])[0]?.[0] || 'unknown';

  const timeline: SessionTimeline = {
    session_id: sessionId,
    dataset,
    time_span: {
      start_ms: tMin,
      end_ms: tMax,
      start_iso: new Date(tMin).toISOString(),
      end_iso: new Date(tMax).toISOString(),
      duration_seconds: durationSeconds,
    },
    events_count: rawEvents.length,
    frames_count: frames.length,
    events_per_min: eventsPerMin,
    gaps_over_30s: gapsOver30s,
    regions,
    event_types: eventTypes,
    layers,
    apps,
    distinct_users: Array.from(users).sort(),
    distinct_machines: Array.from(machines).sort(),
    chunk_dirs_total: sessionInfo.chunks.length,
    chunk_dirs_lacking_events: sessionInfo.chunks.filter(c => !c.hasEvents).length,
    chunk_dirs_lacking_manifest: sessionInfo.chunks.filter(c => !c.hasManifest).length,
    screenshots_referenced: screenshotsReferenced,
    screenshots_present: screenshotsPresent,
    malformed_lines: malformedLinesCount,
  };

  SessionTimelineSchema.parse(timeline);

  const summary: SessionInventorySummary = {
    session_id: sessionId,
    duration_seconds: durationSeconds,
    events_count: rawEvents.length,
    frames_count: frames.length,
    events_per_min: eventsPerMin,
    gaps_over_30s_count: gapsOver30s.length,
    screens_only_seconds: Number(screensOnlySec.toFixed(1)),
    events_only_seconds: Number(eventsOnlySec.toFixed(1)),
    events_and_screens_seconds: Number(bothSec.toFixed(1)),
    primary_mode: primaryMode,
    chunk_dirs_total: sessionInfo.chunks.length,
    chunk_dirs_lacking_events: sessionInfo.chunks.filter(c => !c.hasEvents).length,
    chunk_dirs_lacking_manifest: sessionInfo.chunks.filter(c => !c.hasManifest).length,
    screenshots_referenced: screenshotsReferenced,
    screenshots_present: screenshotsPresent,
    malformed_lines: malformedLinesCount,
    top_app: topApp,
    user_hash: Array.from(users)[0],
    machine_id: Array.from(machines)[0],
  };

  // Write timeline.json
  const sessionArtifactDir = path.join(projectRoot, 'artifacts', dataset, sessionId);
  writeJSONAtomic(path.join(sessionArtifactDir, 'timeline.json'), timeline);

  // Backward-compatible s0_preflight.json
  const preflightReport: PreflightReport = {
    sessionId,
    dataset,
    createdAt: new Date().toISOString(),
    totalChunks: sessionInfo.chunks.length,
    chunksWithEvents: sessionInfo.chunks.filter(c => c.hasEvents).length,
    chunksWithManifest: sessionInfo.chunks.filter(c => c.hasManifest).length,
    chunksWithScreenshots: sessionInfo.chunks.filter(c => c.hasScreenshots).length,
    totalRawEvents: rawEvents.length,
    totalScreenshots: frames.length,
    hasGroundTruth: sessionInfo.hasGt,
    hasGroundTruthManifest: sessionInfo.hasGtManifest,
    gtManifestExecutionsCount: sessionInfo.gtManifestData?.expected_boundaries?.length,
    eventTypesBreakdown: eventTypes,
    layerBreakdown: layers,
    processBreakdown: apps,
    timeSpan: {
      firstEventIso: rawEvents[0]?.timestamp_iso,
      lastEventIso: rawEvents[rawEvents.length - 1]?.timestamp_iso,
      durationSeconds,
    },
    missingScreenshotsReferencedCount: Math.max(0, screenshotsReferenced - screenshotsPresent),
    chunks: sessionInfo.chunks.map(c => ({
      chunkDirName: c.chunkDirName,
      hasEvents: c.hasEvents,
      eventsCount: rawEvents.filter(e => e.correlation?.chunk_id === c.chunkDirName).length,
      hasManifest: c.hasManifest,
      hasScreenshots: c.hasScreenshots,
      screenshotFilesCount: c.screenshotFiles.length,
    })),
  };
  PreflightReportSchema.parse(preflightReport);
  writeJSONAtomic(path.join(sessionArtifactDir, 's0_preflight.json'), preflightReport);

  return { timeline, summary };
}

export async function runS0Preflight(
  targetSessionId?: string,
  targetDataset: DatasetName = 'A',
  projectRoot: string = process.cwd(),
  limit?: number
): Promise<DatasetInventory> {
  const sessionsToProcess = targetSessionId
    ? [targetSessionId]
    : listSessions(targetDataset, projectRoot);

  if (sessionsToProcess.length === 0) {
    throw new Error(`No sessions found for dataset ${targetDataset}`);
  }

  const summaries: SessionInventorySummary[] = [];
  let totalEvents = 0;
  let totalFrames = 0;
  let totalDurationSec = 0;
  let totalScreensOnlySec = 0;
  let totalEventsOnlySec = 0;
  let totalBothSec = 0;

  for (const sesId of sessionsToProcess) {
    const { summary } = await processSessionS0(sesId, targetDataset, projectRoot, limit);
    summaries.push(summary);

    totalEvents += summary.events_count;
    totalFrames += summary.frames_count;
    totalDurationSec += summary.duration_seconds;
    totalScreensOnlySec += summary.screens_only_seconds;
    totalEventsOnlySec += summary.events_only_seconds;
    totalBothSec += summary.events_and_screens_seconds;
  }

  const datasetInventory: DatasetInventory = {
    dataset: targetDataset,
    generated_at: new Date().toISOString(),
    total_sessions: summaries.length,
    total_events: totalEvents,
    total_frames: totalFrames,
    total_duration_hours: Number((totalDurationSec / 3600).toFixed(2)),
    total_screens_only_hours: Number((totalScreensOnlySec / 3600).toFixed(2)),
    total_events_only_hours: Number((totalEventsOnlySec / 3600).toFixed(2)),
    total_events_and_screens_hours: Number((totalBothSec / 3600).toFixed(2)),
    sessions_with_screens_only: summaries.filter(s => s.screens_only_seconds > 0).length,
    sessions_with_events_only: summaries.filter(s => s.events_only_seconds > 0).length,
    sessions_with_both: summaries.filter(s => s.events_and_screens_seconds > 0).length,
    sessions: summaries,
  };

  DatasetInventorySchema.parse(datasetInventory);

  // Write artifacts/<ds>/inventory.json
  const datasetArtifactDir = path.join(projectRoot, 'artifacts', targetDataset);
  writeJSONAtomic(path.join(datasetArtifactDir, 'inventory.json'), datasetInventory);

  // Write artifacts/summaries/inventory_<ds>.md
  const summariesDir = path.join(projectRoot, 'artifacts', 'summaries');
  if (!fs.existsSync(summariesDir)) {
    fs.mkdirSync(summariesDir, { recursive: true });
  }

  const mdLines: string[] = [];
  mdLines.push(`# Dataset ${targetDataset} Inventory Summary Report`);
  mdLines.push(`**Generated At**: ${datasetInventory.generated_at}`);
  mdLines.push(`**Total Sessions**: ${datasetInventory.total_sessions} | **Total Events**: ${datasetInventory.total_events} | **Total Frames**: ${datasetInventory.total_frames} | **Total Span**: ${datasetInventory.total_duration_hours}h`);
  mdLines.push('');
  mdLines.push(`- **Events + Screens Span**: ${datasetInventory.total_events_and_screens_hours}h (${datasetInventory.sessions_with_both} sessions)`);
  mdLines.push(`- **Screens-Only Span**: ${datasetInventory.total_screens_only_hours}h (${datasetInventory.sessions_with_screens_only} sessions)`);
  mdLines.push(`- **Events-Only Span**: ${datasetInventory.total_events_only_hours}h (${datasetInventory.sessions_with_events_only} sessions)`);
  mdLines.push('');
  mdLines.push('| Session ID | Duration (min) | Events | Frames | Ev/min | Gaps >30s | Both (min) | Screens Only (min) | Ev Only (min) | Chunks (lacking ev/man) | Malformed |');
  mdLines.push('|---|---|---|---|---|---|---|---|---|---|---|');

  for (const s of summaries) {
    const durM = (s.duration_seconds / 60).toFixed(1);
    const bothM = (s.events_and_screens_seconds / 60).toFixed(1);
    const scrM = (s.screens_only_seconds / 60).toFixed(1);
    const evM = (s.events_only_seconds / 60).toFixed(1);
    const chunkStat = `${s.chunk_dirs_total} (${s.chunk_dirs_lacking_events}/${s.chunk_dirs_lacking_manifest})`;
    mdLines.push(`| \`${s.session_id}\` | ${durM} | ${s.events_count} | ${s.frames_count} | ${s.events_per_min} | ${s.gaps_over_30s_count} | ${bothM} | ${scrM} | ${evM} | ${chunkStat} | ${s.malformed_lines} |`);
  }

  fs.writeFileSync(path.join(summariesDir, `inventory_${targetDataset.toLowerCase()}.md`), mdLines.join('\n'), 'utf8');

  return datasetInventory;
}
