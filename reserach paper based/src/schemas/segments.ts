import { z } from 'zod';

export const SegmentLineSchema = z.object({
  session_id: z.string().min(1),
  start: z.string().regex(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/, 'Must be ISO 8601 UTC string ending with Z'),
  end: z.string().regex(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/, 'Must be ISO 8601 UTC string ending with Z'),
  label: z.string().min(1),
}).strict(); // STRICT: exactly these four keys, nothing else

export type SegmentLine = z.infer<typeof SegmentLineSchema>;
