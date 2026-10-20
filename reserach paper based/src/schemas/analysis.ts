import { z } from 'zod';

export const AutomationCandidateSchema = z.object({
  rank: z.number().int().positive(),
  process_label: z.string(),
  process_name: z.string(),
  execution_count: z.number().int().nonnegative(),
  total_time_seconds: z.number().nonnegative(),
  mean_time_seconds: z.number().nonnegative(),
  std_dev_seconds: z.number().nonnegative(),
  people_involved: z.number().int().nonnegative(),
  applications: z.array(z.string()),
  pattern_variations_count: z.number().int().nonnegative(),
  rule_determinism_score: z.number().min(0).max(10), // 10 = completely deterministic rules
  data_access_difficulty: z.enum(['low', 'medium', 'high']),
  governance_risk: z.enum(['low', 'medium', 'high']),
  estimated_roi_score: z.number(),
  recommendation_reason: z.string(),
});

export const AnalysisOutputSchema = z.object({
  sessionId: z.string(),
  createdAt: z.string(),
  totalProcessesObserved: z.number().int().nonnegative(),
  totalExecutionsObserved: z.number().int().nonnegative(),
  candidates: z.array(AutomationCandidateSchema),
  topCandidate: z.string(),
  justification: z.string(),
});

export type AutomationCandidate = z.infer<typeof AutomationCandidateSchema>;
export type AnalysisOutput = z.infer<typeof AnalysisOutputSchema>;
