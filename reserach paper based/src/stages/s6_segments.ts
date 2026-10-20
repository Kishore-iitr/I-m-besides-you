import path from 'node:path';
import { DatasetName, ExecutionSegment } from '../types.js';
import { readJSON, readJSONL, writeJSONL } from '../io/jsonl.js';
import { Activity } from '../schemas/activities.js';
import { TaskThreadsOutput } from '../schemas/taskThreads.js';
import { NormalizedEvent } from '../schemas/norm.js';
import { SegmentLineSchema } from '../schemas/segments.js';

export async function runS6Segments(
  sessionId: string,
  dataset: DatasetName,
  projectRoot: string = process.cwd()
): Promise<{ segmentsCount: number; labelsCount: number }> {
  const artifactsDir = path.join(projectRoot, 'artifacts', dataset, sessionId);
  const activitiesPath = path.join(artifactsDir, 's4_activities.jsonl');
  const threadsPath = path.join(artifactsDir, 's5_task_threads.json');
  const normEventsPath = path.join(artifactsDir, 's1_normalized.jsonl');

  const activities = await readJSONL<Activity>(activitiesPath);
  const taskThreads = readJSON<TaskThreadsOutput>(threadsPath);
  const normEvents = await readJSONL<NormalizedEvent>(normEventsPath);

  if (activities.length === 0) {
    throw new Error(`No activities found at ${activitiesPath}`);
  }

  // Create lookup for activity -> canonical label
  const actToLabel = new Map<string, string>();
  for (const assign of taskThreads.assignments) {
    actToLabel.set(assign.activity_id, assign.canonical_root_label);
  }

  // Event timestamp lookup for snapping
  const eventTimestamps = normEvents.map(e => e.timestamp_ms).sort((a, b) => a - b);

  function snapToNearestEvent(targetMs: number): number {
    if (eventTimestamps.length === 0) return targetMs;
    let closest = eventTimestamps[0];
    let minDiff = Math.abs(targetMs - closest);
    for (let i = 1; i < eventTimestamps.length; i++) {
      const diff = Math.abs(targetMs - eventTimestamps[i]);
      if (diff < minDiff) {
        minDiff = diff;
        closest = eventTimestamps[i];
      } else if (eventTimestamps[i] > targetMs) {
        break;
      }
    }
    return closest;
  }

  // Group activities into executions
  interface ExecutionGroup {
    label: string;
    caseId: string;
    startMs: number;
    endMs: number;
  }

  const execGroups: ExecutionGroup[] = [];

  for (let i = 0; i < activities.length; i++) {
    const act = activities[i];
    const label = actToLabel.get(act.activity_id) || act.provisional_label || 'general_backoffice';
    const caseId = act.case_ids[0] || '';

    if (execGroups.length > 0) {
      const prev = execGroups[execGroups.length - 1];
      const sameLabel = prev.label === label;
      const sameCase = prev.caseId && caseId ? prev.caseId === caseId : true;
      const gap = act.start_ms - prev.endMs;

      // Merge if same label and same case and reasonable gap
      if (sameLabel && sameCase && gap <= 15000) {
        prev.endMs = Math.max(prev.endMs, act.end_ms);
        continue;
      }
    }

    execGroups.push({
      label,
      caseId,
      startMs: act.start_ms,
      endMs: act.end_ms,
    });
  }

  const segments: ExecutionSegment[] = [];

  for (const group of execGroups) {
    const snappedStart = snapToNearestEvent(group.startMs);
    const snappedEnd = snapToNearestEvent(group.endMs);

    const startIso = new Date(snappedStart).toISOString().replace(/\.\d{3}Z$/, 'Z');
    const endIso = new Date(snappedEnd).toISOString().replace(/\.\d{3}Z$/, 'Z');

    const seg: ExecutionSegment = {
      session_id: sessionId,
      start: startIso,
      end: endIso,
      label: group.label,
    };

    // Strict validation of the 4 keys
    SegmentLineSchema.parse(seg);
    segments.push(seg);
  }

  // Write artifact
  const outPath = path.join(artifactsDir, 'segments.jsonl');
  await writeJSONL(outPath, segments);

  // Also write to root segments.jsonl
  const rootDeliverablePath = path.join(projectRoot, 'segments.jsonl');
  await writeJSONL(rootDeliverablePath, segments);

  const uniqueLabels = new Set(segments.map(s => s.label));

  return {
    segmentsCount: segments.length,
    labelsCount: uniqueLabels.size,
  };
}
