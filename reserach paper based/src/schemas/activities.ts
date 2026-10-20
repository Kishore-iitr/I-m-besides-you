import { z } from 'zod';

export const ActivitySchema = z.object({
  activity_id: z.string(),
  session_id: z.string(),
  start_ms: z.number().int(),
  start_iso: z.string(),
  end_ms: z.number().int(),
  end_iso: z.string(),
  burst_ids: z.array(z.string()),
  semantic_action_ids: z.array(z.string()),
  summary: z.string().min(1),
  app_names: z.array(z.string()),
  case_ids: z.array(z.string()),
  provisional_label: z.string(),
});

export type Activity = z.infer<typeof ActivitySchema>;
