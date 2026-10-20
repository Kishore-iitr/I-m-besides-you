import { z } from 'zod';

export const CanonicalExecutionSchema = z.object({
  exec_id: z.string(),
  code: z.string(),
  family_name: z.string(),
  variant: z.string().nullable().optional(),
  case_id: z.string(),
  start_iso: z.string(),
  end_iso: z.string(),
  start_ms: z.number().int(),
  end_ms: z.number().int(),
  apps: z.array(z.string()),
  continues_from_prev: z.boolean().optional(),
  continues_to_next: z.boolean().optional(),
  split_id: z.string().nullable().optional(),
  phase: z.number().int().optional(),
  seq: z.number().int().optional(),
});

export const CanonicalGtFileSchema = z.object({
  sessionId: z.string(),
  runId: z.string().optional(),
  operator: z.string().optional(),
  department: z.string().optional(),
  executionsCount: z.number().int().nonnegative(),
  familiesCount: z.number().int().nonnegative(),
  executions: z.array(CanonicalExecutionSchema),
});

export const ClockAlignmentReportSchema = z.object({
  sessionId: z.string(),
  hasGroundTruth: z.boolean(),
  estimatedOffsetMs: z.number(),
  confidence: z.enum(['high', 'medium', 'low', 'unaligned']),
  evidence: z.array(z.object({
    eventType: z.string(),
    gtIso: z.string(),
    eventIso: z.string(),
    offsetMs: z.number(),
    matchedOn: z.string(),
  })),
  medianOffsetMs: z.number(),
  p90OffsetMs: z.number(),
});

export type CanonicalExecution = z.infer<typeof CanonicalExecutionSchema>;
export type CanonicalGtFile = z.infer<typeof CanonicalGtFileSchema>;
export type ClockAlignmentReport = z.infer<typeof ClockAlignmentReportSchema>;
