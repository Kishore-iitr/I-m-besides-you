export interface ClusteringMetricsResult {
  ari: number;
  nmi: number;
  purity: number;
}

function comb2(n: number): number {
  return n < 2 ? 0 : (n * (n - 1)) / 2;
}

export function computeClusteringMetrics(
  trueLabels: string[],
  predLabels: string[]
): ClusteringMetricsResult {
  if (trueLabels.length !== predLabels.length || trueLabels.length === 0) {
    return { ari: 0, nmi: 0, purity: 0 };
  }

  const n = trueLabels.length;

  // Build contingency table
  const contingency: Record<string, Record<string, number>> = {};
  const rowSums: Record<string, number> = {};
  const colSums: Record<string, number> = {};

  for (let k = 0; k < n; k++) {
    const t = trueLabels[k];
    const p = predLabels[k];

    if (!contingency[t]) contingency[t] = {};
    contingency[t][p] = (contingency[t][p] || 0) + 1;

    rowSums[t] = (rowSums[t] || 0) + 1;
    colSums[p] = (colSums[p] || 0) + 1;
  }

  // ARI calculation
  let sumNijComb2 = 0;
  for (const t in contingency) {
    for (const p in contingency[t]) {
      sumNijComb2 += comb2(contingency[t][p]);
    }
  }

  let sumAiComb2 = 0;
  for (const t in rowSums) {
    sumAiComb2 += comb2(rowSums[t]);
  }

  let sumBjComb2 = 0;
  for (const p in colSums) {
    sumBjComb2 += comb2(colSums[p]);
  }

  const totalComb2 = comb2(n);
  const expectedIndex = totalComb2 > 0 ? (sumAiComb2 * sumBjComb2) / totalComb2 : 0;
  const maxIndex = (sumAiComb2 + sumBjComb2) / 2;

  let ari = 0;
  const denom = maxIndex - expectedIndex;
  if (denom > 0) {
    ari = (sumNijComb2 - expectedIndex) / denom;
  } else if (sumNijComb2 === expectedIndex) {
    ari = 1.0;
  }

  // Purity
  let maxMatchedSum = 0;
  for (const p in colSums) {
    let maxInCluster = 0;
    for (const t in contingency) {
      const count = contingency[t][p] || 0;
      if (count > maxInCluster) maxInCluster = count;
    }
    maxMatchedSum += maxInCluster;
  }
  const purity = n > 0 ? maxMatchedSum / n : 0;

  // NMI calculation (Shannon entropy)
  let mi = 0;
  for (const t in contingency) {
    for (const p in contingency[t]) {
      const nij = contingency[t][p];
      if (nij > 0) {
        mi += (nij / n) * Math.log2((n * nij) / (rowSums[t] * colSums[p]));
      }
    }
  }

  let hTrue = 0;
  for (const t in rowSums) {
    const p = rowSums[t] / n;
    if (p > 0) hTrue -= p * Math.log2(p);
  }

  let hPred = 0;
  for (const p in colSums) {
    const pr = colSums[p] / n;
    if (pr > 0) hPred -= pr * Math.log2(pr);
  }

  const nmiDenom = Math.sqrt(hTrue * hPred);
  const nmi = nmiDenom > 0 ? mi / nmiDenom : (hTrue === 0 && hPred === 0 ? 1 : 0);

  return {
    ari: Math.round(Math.max(-1, Math.min(1, ari)) * 10000) / 10000,
    nmi: Math.round(Math.max(0, Math.min(1, nmi)) * 10000) / 10000,
    purity: Math.round(Math.max(0, Math.min(1, purity)) * 10000) / 10000,
  };
}
