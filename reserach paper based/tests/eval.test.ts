import { describe, it, expect } from 'vitest';
import { evaluateBoundaries, BoundaryPoint } from '../src/eval/boundary.js';
import { computeClusteringMetrics } from '../src/eval/ari.js';

describe('Evaluation Metrics', () => {
  it('computes boundary precision, recall, and F1 within tolerance', () => {
    const gt: BoundaryPoint[] = [
      { timeMs: 10000, type: 'start', id: 'gt1' },
      { timeMs: 30000, type: 'end', id: 'gt1' },
      { timeMs: 40000, type: 'start', id: 'gt2' },
      { timeMs: 60000, type: 'end', id: 'gt2' },
    ];

    // Predictions slightly shifted (+2s)
    const pred: BoundaryPoint[] = [
      { timeMs: 12000, type: 'start', id: 'p1' },
      { timeMs: 29000, type: 'end', id: 'p1' },
      { timeMs: 41000, type: 'start', id: 'p2' },
      { timeMs: 62000, type: 'end', id: 'p2' },
    ];

    const res = evaluateBoundaries(pred, gt, 5); // 5s tolerance
    expect(res.truePositives).toBe(4);
    expect(res.falsePositives).toBe(0);
    expect(res.falseNegatives).toBe(0);
    expect(res.precision).toBe(1.0);
    expect(res.recall).toBe(1.0);
    expect(res.f1).toBe(1.0);
    expect(res.meanOffsetSeconds).toBeCloseTo(1.5, 1);
  });

  it('computes ARI and NMI for identical cluster assignments', () => {
    const trueLabels = ['A', 'A', 'A', 'B', 'B', 'C', 'C'];
    const predLabels = ['X', 'X', 'X', 'Y', 'Y', 'Z', 'Z']; // Permuted label text
    const res = computeClusteringMetrics(trueLabels, predLabels);
    expect(res.ari).toBe(1.0);
    expect(res.nmi).toBe(1.0);
    expect(res.purity).toBe(1.0);
  });

  it('computes ARI for mismatched cluster assignments', () => {
    const trueLabels = ['A', 'A', 'B', 'B'];
    const predLabels = ['X', 'Y', 'X', 'Y'];
    const res = computeClusteringMetrics(trueLabels, predLabels);
    expect(res.ari).toBeLessThan(0.5);
  });
});
