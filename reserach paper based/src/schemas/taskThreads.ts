import { z } from 'zod';

export const TaskThreadRootSchema = z.object({
  canonical_root_id: z.string().min(1),
  label: z.string().min(1),
  objective: z.string().min(1),
  deliverable: z.string().min(1),
  success_criteria: z.string().min(1),
  summary: z.string().default(''),
  family_anchors: z.array(z.string()).default([]),
  case_anchors: z.array(z.string()).default([]),
  activity_ids: z.array(z.string()).default([]),
  burst_ids: z.array(z.string()).default([]),
  observed_apps: z.array(z.string()).default([]),
  event_count: z.number().int().nonnegative().default(0),
});

export const TaskThreadAssignmentSchema = z.object({
  activity_id: z.string(),
  canonical_root_id: z.string(),
  canonical_root_label: z.string(),
  confidence: z.number().min(0).max(1).optional(),
});

export const TaskThreadsOutputSchema = z.object({
  sessionId: z.string(),
  createdAt: z.string(),
  roots: z.array(TaskThreadRootSchema),
  assignments: z.array(TaskThreadAssignmentSchema),
});

export type TaskThreadRoot = z.infer<typeof TaskThreadRootSchema>;
export type TaskThreadsOutput = z.infer<typeof TaskThreadsOutputSchema>;
