import { z } from 'zod';

export const RawEventSchema = z.object({
  schema_version: z.string().optional(),
  event_id: z.string().optional(),
  session_id: z.string().optional(),
  timestamp_ms: z.number().int(),
  timestamp_iso: z.string().optional(),
  layer: z.string().default('L1'),
  event_type: z.string(),
  source: z.object({
    agent_version: z.string().optional(),
    machine_id: z.string().optional(),
    os: z.string().optional(),
    username_hash: z.string().optional(),
  }).passthrough().optional(),
  context: z.object({
    active_app: z.object({
      process_name: z.string().optional(),
      app_name: z.string().optional(),
      window_title: z.string().optional(),
      process_id: z.number().optional(),
    }).passthrough().optional().nullable(),
    active_monitor: z.any().optional().nullable(),
    active_browser_tab: z.any().optional().nullable(),
    visible_windows: z.array(z.any()).optional().nullable(),
    open_apps: z.array(z.any()).optional().nullable(),
    extracted_text: z.object({
      text: z.string().optional(),
      source: z.string().optional(),
      char_count: z.number().optional(),
      truncated: z.boolean().optional(),
    }).passthrough().optional().nullable(),
  }).passthrough().optional(),
  correlation: z.object({
    triggered_by: z.string().optional().nullable(),
    correlated_events: z.array(z.string()).optional(),
    sequence_number: z.number().optional(),
    chunk_id: z.string().optional(),
    ms_since_last_event: z.number().optional().nullable(),
  }).passthrough().optional(),
  payload: z.record(z.string(), z.any()).default({}),
  metadata: z.record(z.string(), z.any()).optional(),
  extensions: z.record(z.string(), z.any()).optional(),
}).passthrough();

export type RawEventValidated = z.infer<typeof RawEventSchema>;

export const FrameSchema = z.object({
  timestamp_ms: z.number().int(),
  timestamp_iso: z.string(),
  filename: z.string(),
  path: z.string(),
  exists: z.boolean(),
  source: z.enum(['event', 'folder']),
  monitor: z.number().int().optional(),
  event_id: z.string().optional(),
});

export type Frame = z.infer<typeof FrameSchema>;

export const ModeRegionSchema = z.object({
  mode: z.enum(['events+screens', 'events-only', 'screens-only']),
  start_ms: z.number().int(),
  end_ms: z.number().int(),
  start_iso: z.string(),
  end_iso: z.string(),
  duration_seconds: z.number().nonnegative(),
  events_count: z.number().int().nonnegative(),
  frames_count: z.number().int().nonnegative(),
});

export type ModeRegion = z.infer<typeof ModeRegionSchema>;

export const GapSchema = z.object({
  start_ms: z.number().int(),
  end_ms: z.number().int(),
  duration_seconds: z.number().nonnegative(),
});

export type Gap = z.infer<typeof GapSchema>;

export const SessionTimelineSchema = z.object({
  session_id: z.string(),
  dataset: z.enum(['A', 'B']),
  time_span: z.object({
    start_ms: z.number().int(),
    end_ms: z.number().int(),
    start_iso: z.string(),
    end_iso: z.string(),
    duration_seconds: z.number().nonnegative(),
  }),
  events_count: z.number().int().nonnegative(),
  frames_count: z.number().int().nonnegative(),
  events_per_min: z.number().nonnegative(),
  gaps_over_30s: z.array(GapSchema),
  regions: z.array(ModeRegionSchema),
  event_types: z.record(z.string(), z.number().int().nonnegative()),
  layers: z.record(z.string(), z.number().int().nonnegative()),
  apps: z.record(z.string(), z.number().int().nonnegative()),
  distinct_users: z.array(z.string()),
  distinct_machines: z.array(z.string()),
  chunk_dirs_total: z.number().int().nonnegative(),
  chunk_dirs_lacking_events: z.number().int().nonnegative(),
  chunk_dirs_lacking_manifest: z.number().int().nonnegative(),
  screenshots_referenced: z.number().int().nonnegative(),
  screenshots_present: z.number().int().nonnegative(),
  malformed_lines: z.number().int().nonnegative(),
});

export type SessionTimeline = z.infer<typeof SessionTimelineSchema>;

export const SessionInventorySummarySchema = z.object({
  session_id: z.string(),
  duration_seconds: z.number().nonnegative(),
  events_count: z.number().int().nonnegative(),
  frames_count: z.number().int().nonnegative(),
  events_per_min: z.number().nonnegative(),
  gaps_over_30s_count: z.number().int().nonnegative(),
  screens_only_seconds: z.number().nonnegative(),
  events_only_seconds: z.number().nonnegative(),
  events_and_screens_seconds: z.number().nonnegative(),
  primary_mode: z.enum(['events+screens', 'events-only', 'screens-only']),
  chunk_dirs_total: z.number().int().nonnegative(),
  chunk_dirs_lacking_events: z.number().int().nonnegative(),
  chunk_dirs_lacking_manifest: z.number().int().nonnegative(),
  screenshots_referenced: z.number().int().nonnegative(),
  screenshots_present: z.number().int().nonnegative(),
  malformed_lines: z.number().int().nonnegative(),
  top_app: z.string(),
  user_hash: z.string().optional(),
  machine_id: z.string().optional(),
});

export type SessionInventorySummary = z.infer<typeof SessionInventorySummarySchema>;

export const DatasetInventorySchema = z.object({
  dataset: z.enum(['A', 'B']),
  generated_at: z.string(),
  total_sessions: z.number().int().nonnegative(),
  total_events: z.number().int().nonnegative(),
  total_frames: z.number().int().nonnegative(),
  total_duration_hours: z.number().nonnegative(),
  total_screens_only_hours: z.number().nonnegative(),
  total_events_only_hours: z.number().nonnegative(),
  total_events_and_screens_hours: z.number().nonnegative(),
  sessions_with_screens_only: z.number().int().nonnegative(),
  sessions_with_events_only: z.number().int().nonnegative(),
  sessions_with_both: z.number().int().nonnegative(),
  sessions: z.array(SessionInventorySummarySchema),
});

export type DatasetInventory = z.infer<typeof DatasetInventorySchema>;

// Backward compatibility with previous preflight schema
export const PreflightChunkReportSchema = z.object({
  chunkDirName: z.string(),
  hasEvents: z.boolean(),
  eventsCount: z.number().int().nonnegative(),
  hasManifest: z.boolean(),
  hasScreenshots: z.boolean(),
  screenshotFilesCount: z.number().int().nonnegative(),
});

export const PreflightReportSchema = z.object({
  sessionId: z.string(),
  dataset: z.enum(['A', 'B']),
  createdAt: z.string(),
  totalChunks: z.number().int().nonnegative(),
  chunksWithEvents: z.number().int().nonnegative(),
  chunksWithManifest: z.number().int().nonnegative(),
  chunksWithScreenshots: z.number().int().nonnegative(),
  totalRawEvents: z.number().int().nonnegative(),
  totalScreenshots: z.number().int().nonnegative(),
  hasGroundTruth: z.boolean(),
  hasGroundTruthManifest: z.boolean(),
  gtEventsCount: z.number().int().nonnegative().optional(),
  gtManifestExecutionsCount: z.number().int().nonnegative().optional(),
  eventTypesBreakdown: z.record(z.string(), z.number().int().nonnegative()),
  layerBreakdown: z.record(z.string(), z.number().int().nonnegative()),
  processBreakdown: z.record(z.string(), z.number().int().nonnegative()),
  timeSpan: z.object({
    firstEventIso: z.string().optional(),
    lastEventIso: z.string().optional(),
    durationSeconds: z.number().nonnegative().optional(),
  }),
  missingScreenshotsReferencedCount: z.number().int().nonnegative(),
  chunks: z.array(PreflightChunkReportSchema),
});

export type PreflightReport = z.infer<typeof PreflightReportSchema>;
