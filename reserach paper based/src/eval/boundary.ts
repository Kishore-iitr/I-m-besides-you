export interface BoundaryPoint {
  timeMs: number;
  type: 'start' | 'end';
  label?: string;
  id: string;
}

export interface BoundaryMetricsResult {
  toleranceSec: number;
  truePositives: number;
  falsePositives: number;
  falseNegatives: number;
  precision: number;
  recall: number;
  f1: number;
  meanOffsetSeconds: number;
}

export function evaluateBoundaries(
  predictedBoundaries: BoundaryPoint[],
  gtBoundaries: BoundaryPoint[],
  toleranceSec: number
): BoundaryMetricsResult {
  const toleranceMs = toleranceSec * 1000;
  const matchedGtIndices = new Set<number>();
  let tp = 0;
  let offsetsSum = 0;

  // For each predicted boundary, find closest unmatched GT boundary of matching type
  for (const pred of predictedBoundaries) {
    let closestIndex = -1;
    let minDiff = Infinity;

    for (let i = 0; i < gtBoundaries.length; i++) {
      if (matchedGtIndices.has(i)) continue;
      const gt = gtBoundaries[i];
      if (pred.type !== gt.type) continue;

      const diff = Math.abs(pred.timeMs - gt.timeMs);
      if (diff <= toleranceMs && diff < minDiff) {
        minDiff = diff;
        closestIndex = i;
      }
    }

    if (closestIndex !== -1) {
      matchedGtIndices.add(closestIndex);
      tp++;
      offsetsSum += minDiff;
    }
  }

  const fp = predictedBoundaries.length - tp;
  const fn = gtBoundaries.length - tp;

  const precision = predictedBoundaries.length > 0 ? tp / predictedBoundaries.length : 0;
  const recall = gtBoundaries.length > 0 ? tp / gtBoundaries.length : 0;
  const f1 = precision + recall > 0 ? (2 * precision * recall) / (precision + recall) : 0;
  const meanOffsetSeconds = tp > 0 ? (offsetsSum / tp) / 1000 : 0;

  return {
    toleranceSec,
    truePositives: tp,
    falsePositives: fp,
    falseNegatives: fn,
    precision: Math.round(precision * 10000) / 10000,
    recall: Math.round(recall * 10000) / 10000,
    f1: Math.round(f1 * 10000) / 10000,
    meanOffsetSeconds: Math.round(meanOffsetSeconds * 100) / 100,
  };
}
