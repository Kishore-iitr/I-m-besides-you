import { z } from 'zod';

export const PrototypeSpecSchema = z.object({
  targetProcess: z.string(),
  prototypeType: z.enum(['cli_script', 'ai_agent', 'workflow_engine', 'desktop_app']),
  entrypointCommand: z.string(),
  description: z.string(),
  scopeCovered: z.string(),
  deferredScope: z.string(),
  remainingManualWork: z.string(),
  expectedRoiHoursPerYear: z.number().nonnegative(),
  risksAndMitigations: z.array(z.object({
    risk: z.string(),
    evidenceFromLogs: z.string(),
    mitigation: z.string(),
  })),
  demoRunOutput: z.string(),
});

export type PrototypeSpec = z.infer<typeof PrototypeSpecSchema>;
