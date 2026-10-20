import { z } from 'zod';
import { FrameSchema } from './preflight.js';

export const TypedTextSchema = z.object({
  ts_start: z.number().int(),
  ts_end: z.number().int(),
  app: z.string(),
  field: z.string(),
  text: z.string(),
  confidence: z.number().min(0).max(1),
  ime_suspected: z.boolean().optional(),
});

export type TypedText = z.infer<typeof TypedTextSchema>;

export const IdentifierKindSchema = z.enum(['case_id', 'entity', 'doc_no', 'other']);

export const IdentifierSchema = z.object({
  value: z.string(),
  kind: IdentifierKindSchema,
  first_ts: z.number().int(),
  last_ts: z.number().int(),
  sources: z.array(z.string()),
});

export type Identifier = z.infer<typeof IdentifierSchema>;

export const NormalizedEventSchema = z.object({
  event_id: z.string(),
  session_id: z.string(),
  chunk_id: z.string(),
  timestamp_ms: z.number().int(),
  timestamp_iso: z.string(),
  layer: z.string(),
  event_type: z.string(),
  app_name: z.string(),
  process_name: z.string(),
  window_title: z.string(),
  clean_title: z.string(),
  title_template: z.string().optional(),
  extracted_text: z.string().optional(),
  typed_text: z.string().optional(),
  extracted_case_ids: z.array(z.string()),
  screenshot_file: z.string().optional(),
  payload_summary: z.string(),
});

export type NormalizedEvent = z.infer<typeof NormalizedEventSchema>;

export const BurstCompactEventSchema = z.object({
  event_id: z.string(),
  event_type: z.string(),
  timestamp_ms: z.number().int(),
  app_name: z.string().optional(),
});

export const BurstClipboardChangeSchema = z.object({
  timestamp_ms: z.number().int(),
  text_length: z.number().int().optional(),
});

export const BurstSchema = z.object({
  burst_id: z.string(),
  session_id: z.string(),
  start_ms: z.number().int(),
  start_iso: z.string(),
  end_ms: z.number().int(),
  end_iso: z.string(),
  duration_ms: z.number().int().nonnegative(),
  app_name: z.string(),
  window_title: z.string(),
  clean_title: z.string(),
  title_template: z.string().optional(),
  event_count: z.number().int().nonnegative(),
  event_types: z.record(z.string(), z.number().int().nonnegative()),
  events: z.array(BurstCompactEventSchema).optional(),
  typed_texts: z.array(TypedTextSchema).optional(),
  clipboard_changes: z.array(BurstClipboardChangeSchema).optional(),
  titles: z.array(z.string()).optional(),
  extracted_text: z.string().optional(),
  case_ids: z.array(z.string()),
  before_frame: FrameSchema.nullable().optional(),
  after_frame: FrameSchema.nullable().optional(),
  gap_before_s: z.number().nonnegative().optional(),
  dwell_s: z.number().nonnegative().optional(),
  event_rate: z.number().nonnegative().optional(),
  screenshot_file: z.string().optional(),
  has_screenshot: z.boolean(),
  input_mode: z.enum(['events_and_screens', 'events_only', 'screens_only']),
  signature: z.string(),
});

export type Burst = z.infer<typeof BurstSchema>;
