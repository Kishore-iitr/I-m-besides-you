import { z } from 'zod';
import { BurstSchema } from './norm.js';

export const GroundedBurstSchema = BurstSchema.extend({
  semantic_action: z.string().min(1),
  ui_target: z.string(),
  intent: z.string(),
  grounding_mode: z.enum(['mock', 'vision', 'ocr_text', 'rule']),
});

export type GroundedBurst = z.infer<typeof GroundedBurstSchema>;
