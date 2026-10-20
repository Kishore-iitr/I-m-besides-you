import { z } from 'zod';

export const ProcedureStepSchema = z.object({
  step_id: z.string(),
  name: z.string(),
  description: z.string(),
  app: z.string(),
  action_type: z.string(),
  control_flow: z.enum(['SEQ', 'BRANCH', 'LOOP', 'OPTIONAL']),
  condition: z.string().optional(),
  target_field: z.string().optional(),
  sample_values: z.array(z.string()).default([]),
});

export const ProcedureModelSchema = z.object({
  family_id: z.string(),
  family_name: z.string(),
  domain: z.string(),
  total_executions_observed: z.number().int().nonnegative(),
  mean_duration_sec: z.number().nonnegative(),
  steps: z.array(ProcedureStepSchema),
  variations: z.array(z.object({
    variant_name: z.string(),
    description: z.string(),
    frequency: z.number().nonnegative(),
  })),
  system_dependencies: z.array(z.string()),
});

export const TaskModelsOutputSchema = z.object({
  sessionId: z.string(),
  createdAt: z.string(),
  procedureModels: z.array(ProcedureModelSchema),
});

export type ProcedureModel = z.infer<typeof ProcedureModelSchema>;
export type TaskModelsOutput = z.infer<typeof TaskModelsOutputSchema>;
