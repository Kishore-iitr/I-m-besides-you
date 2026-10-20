import { z } from 'zod';

export const ToleranceMetricsSchema = z.object({
  toleranceSec: z.number(),
  truePositives: z.number().int().nonnegative(),
  falsePositives: z.number().int().nonnegative(),
  falseNegatives: z.number().int().nonnegative(),
  precision: z.number().min(0).max(1),
  recall: z.number().min(0).max(1),
  f1: z.number().min(0).max(1),
  meanOffsetSeconds: z.number(),
});

export const BaselineComparisonSchema = z.object({
  name: z.string(),
  segmentsCount: z.number().int().nonnegative(),
  f1At30s: z.number().min(0).max(1),
  ari: z.number().min(-1).max(1),
});

export const EvaluationReportSchema = z.object({
  sessionId: z.string(),
  evaluatedAt: z.string(),
  predictedSegmentsCount: z.number().int().nonnegative(),
  groundTruthExecutionsCount: z.number().int().nonnegative(),
  uniquePredictedLabels: z.array(z.string()),
  uniqueGroundTruthLabels: z.array(z.string()),
  tolerances: z.array(ToleranceMetricsSchema),
  clustering: z.object({
    ari: z.number().min(-1).max(1),
    nmi: z.number().min(0).max(1),
    purity: z.number().min(0).max(1),
  }),
  temporalOverlap: z.object({
    meanIou: z.number().min(0).max(1),
    coverage: z.number().min(0).max(1),
  }),
  baselines: z.array(BaselineComparisonSchema),
});

export type EvaluationReport = z.infer<typeof EvaluationReportSchema>;
