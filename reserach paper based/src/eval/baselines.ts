import { NormalizedEvent, ExecutionSegment } from '../types.js';
import { CanonicalExecution } from '../schemas/gt.js';
import { evaluateBoundaries, BoundaryPoint } from './boundary.js';
import { computeClusteringMetrics } from './ari.js';
import { BaselineComparisonSchema } from '../schemas/eval.js';
import { z } from 'zod';

type BaselineComparison = z.infer<typeof BaselineComparisonSchema>;

export function generateUniformBaseline(
  events: NormalizedEvent[],
  windowSec: number = 60
): ExecutionSegment[] {
  if (events.length === 0) return [];
  const firstMs = events[0].timestamp_ms;
  const lastMs = events[events.length - 1].timestamp_ms;
  const stepMs = windowSec * 1000;
  const segments: ExecutionSegment[] = [];

  let curStart = firstMs;
  let idx = 1;
  while (curStart < lastMs) {
    const curEnd = Math.min(lastMs, curStart + stepMs);
    segments.push({
      session_id: events[0].session_id,
      start: new Date(curStart).toISOString().replace(/\.\d{3}Z$/, 'Z'),
      end: new Date(curEnd).toISOString().replace(/\.\d{3}Z$/, 'Z'),
      label: `uniform_proc_${idx % 5}`,
    });
    curStart = curEnd;
    idx++;
  }
  return segments;
}

export function generateIdleGapBaseline(
  events: NormalizedEvent[],
  idleThresholdMs: number = 5000
): ExecutionSegment[] {
  if (events.length === 0) return [];
  const segments: ExecutionSegment[] = [];
  let segStart = events[0].timestamp_ms;
  let idx = 1;

  for (let i = 1; i < events.length; i++) {
    const gap = events[i].timestamp_ms - events[i - 1].timestamp_ms;
    if (gap >= idleThresholdMs) {
      segments.push({
        session_id: events[0].session_id,
        start: new Date(segStart).toISOString().replace(/\.\d{3}Z$/, 'Z'),
        end: new Date(events[i - 1].timestamp_ms).toISOString().replace(/\.\d{3}Z$/, 'Z'),
        label: `idle_cluster_${events[i - 1].app_name}`,
      });
      segStart = events[i].timestamp_ms;
      idx++;
    }
  }

  segments.push({
    session_id: events[0].session_id,
    start: new Date(segStart).toISOString().replace(/\.\d{3}Z$/, 'Z'),
    end: new Date(events[events.length - 1].timestamp_ms).toISOString().replace(/\.\d{3}Z$/, 'Z'),
    label: `idle_cluster_${events[events.length - 1].app_name}`,
  });

  return segments;
}

export function evaluateBaselineAgainstGt(
  baselineName: string,
  segments: ExecutionSegment[],
  gtExecutions: CanonicalExecution[],
  events: NormalizedEvent[]
): BaselineComparison {
  const predBoundaries: BoundaryPoint[] = [];
  for (const s of segments) {
    predBoundaries.push({ timeMs: Date.parse(s.start), type: 'start', id: s.start });
    predBoundaries.push({ timeMs: Date.parse(s.end), type: 'end', id: s.end });
  }

  const gtBoundaries: BoundaryPoint[] = [];
  for (const g of gtExecutions) {
    gtBoundaries.push({ timeMs: g.start_ms, type: 'start', id: g.exec_id });
    gtBoundaries.push({ timeMs: g.end_ms, type: 'end', id: g.exec_id });
  }

  const bRes = evaluateBoundaries(predBoundaries, gtBoundaries, 30);

  // Compute event-level clustering
  const trueLabels: string[] = [];
  const predLabels: string[] = [];

  for (const ev of events) {
    const t = ev.timestamp_ms;
    const matchedGt = gtExecutions.find(g => t >= g.start_ms && t <= g.end_ms);
    trueLabels.push(matchedGt ? matchedGt.code : 'NONE');

    const matchedPred = segments.find(s => {
      const sMs = Date.parse(s.start);
      const eMs = Date.parse(s.end);
      return t >= sMs && t <= eMs;
    });
    predLabels.push(matchedPred ? matchedPred.label : 'NONE');
  }

  const cRes = computeClusteringMetrics(trueLabels, predLabels);

  return {
    name: baselineName,
    segmentsCount: segments.length,
    f1At30s: bRes.f1,
    ari: cRes.ari,
  };
}
