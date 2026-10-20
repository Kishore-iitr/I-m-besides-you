import { ExecutionSegment, NormalizedEvent } from '../types.js';
import { CanonicalExecution } from '../schemas/gt.js';
import { EvaluationReport } from '../schemas/eval.js';
import { evaluateBoundaries, BoundaryPoint } from './boundary.js';
import { computeClusteringMetrics } from './ari.js';
import { generateUniformBaseline, generateIdleGapBaseline, evaluateBaselineAgainstGt } from './baselines.js';

export function runEvaluation(
  sessionId: string,
  predictedSegments: ExecutionSegment[],
  gtExecutions: CanonicalExecution[],
  events: NormalizedEvent[],
  tolerancesSec: number[] = [15, 30, 60]
): EvaluationReport {
  const predBoundaries: BoundaryPoint[] = [];
  for (const s of predictedSegments) {
    predBoundaries.push({ timeMs: Date.parse(s.start), type: 'start', id: `${s.label}_start_${s.start}` });
    predBoundaries.push({ timeMs: Date.parse(s.end), type: 'end', id: `${s.label}_end_${s.end}` });
  }

  const gtBoundaries: BoundaryPoint[] = [];
  for (const g of gtExecutions) {
    gtBoundaries.push({ timeMs: g.start_ms, type: 'start', id: `${g.code}_start_${g.exec_id}` });
    gtBoundaries.push({ timeMs: g.end_ms, type: 'end', id: `${g.code}_end_${g.exec_id}` });
  }

  // Tolerance metrics
  const toleranceMetrics = tolerancesSec.map(tol => evaluateBoundaries(predBoundaries, gtBoundaries, tol));

  // Event-level clustering alignment
  const trueLabels: string[] = [];
  const predLabels: string[] = [];

  for (const ev of events) {
    const t = ev.timestamp_ms;
    const matchedGt = gtExecutions.find(g => t >= g.start_ms && t <= g.end_ms);
    trueLabels.push(matchedGt ? matchedGt.code : 'UNRELATED');

    const matchedPred = predictedSegments.find(s => {
      const sMs = Date.parse(s.start);
      const eMs = Date.parse(s.end);
      return t >= sMs && t <= eMs;
    });
    predLabels.push(matchedPred ? matchedPred.label : 'UNRELATED');
  }

  const clustering = computeClusteringMetrics(trueLabels, predLabels);

  // Temporal IoU and coverage
  let iouSum = 0;
  let matchedSegments = 0;

  for (const pred of predictedSegments) {
    const pStart = Date.parse(pred.start);
    const pEnd = Date.parse(pred.end);
    let bestIou = 0;

    for (const gt of gtExecutions) {
      const overlapStart = Math.max(pStart, gt.start_ms);
      const overlapEnd = Math.min(pEnd, gt.end_ms);
      const intersection = Math.max(0, overlapEnd - overlapStart);
      const union = Math.max(0, Math.max(pEnd, gt.end_ms) - Math.min(pStart, gt.start_ms));

      if (union > 0) {
        const iou = intersection / union;
        if (iou > bestIou) {
          bestIou = iou;
        }
      }
    }

    if (bestIou > 0) {
      iouSum += bestIou;
      matchedSegments++;
    }
  }

  const meanIou = matchedSegments > 0 ? iouSum / matchedSegments : 0;

  const totalEventSpan = events.length > 1 ? events[events.length - 1].timestamp_ms - events[0].timestamp_ms : 1;
  const predTotalCovered = predictedSegments.reduce((acc, s) => acc + (Date.parse(s.end) - Date.parse(s.start)), 0);
  const coverage = Math.min(1, Math.max(0, predTotalCovered / totalEventSpan));

  // Baselines comparison
  const uniformSegs = generateUniformBaseline(events, 60);
  const idleSegs = generateIdleGapBaseline(events, 5000);

  const baselines = [
    evaluateBaselineAgainstGt('Uniform 60s window', uniformSegs, gtExecutions, events),
    evaluateBaselineAgainstGt('Idle Gap (>5s) split', idleSegs, gtExecutions, events),
  ];

  return {
    sessionId,
    evaluatedAt: new Date().toISOString(),
    predictedSegmentsCount: predictedSegments.length,
    groundTruthExecutionsCount: gtExecutions.length,
    uniquePredictedLabels: Array.from(new Set(predictedSegments.map(s => s.label))).sort(),
    uniqueGroundTruthLabels: Array.from(new Set(gtExecutions.map(g => g.code))).sort(),
    tolerances: toleranceMetrics,
    clustering,
    temporalOverlap: {
      meanIou: Math.round(meanIou * 10000) / 10000,
      coverage: Math.round(coverage * 10000) / 10000,
    },
    baselines,
  };
}
