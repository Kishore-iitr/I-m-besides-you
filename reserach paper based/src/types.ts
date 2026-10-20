export type DatasetName = 'A' | 'B';

export type InputMode = 'events_and_screens' | 'events_only' | 'screens_only';

export interface RawEvent {
  schema_version?: string;
  event_id?: string;
  session_id?: string;
  timestamp_ms: number;
  timestamp_iso?: string;
  layer: string;
  event_type: string;
  source?: {
    agent_version?: string;
    machine_id?: string;
    os?: string;
    username_hash?: string;
    platform?: string;
  };
  context?: {
    active_app?: {
      process_name?: string;
      app_name?: string;
      window_title?: string;
      process_id?: number;
    } | null;
    active_monitor?: any;
    active_browser_tab?: any;
    visible_windows?: any;
    open_apps?: any;
    extracted_text?: {
      text?: string;
      source?: string;
      char_count?: number;
      truncated?: boolean;
    } | null;
  };
  correlation?: {
    triggered_by?: string | null;
    correlated_events?: string[];
    sequence_number?: number;
    chunk_id?: string;
    ms_since_last_event?: number | null;
  };
  payload: Record<string, any>;
  metadata?: Record<string, any>;
  extensions?: Record<string, any>;
}

export interface Frame {
  timestamp_ms: number;
  timestamp_iso: string;
  filename: string;
  path: string;
  exists: boolean;
  source: 'event' | 'folder';
  monitor?: number;
  event_id?: string;
}

export interface ModeRegion {
  mode: 'events+screens' | 'events-only' | 'screens-only';
  start_ms: number;
  end_ms: number;
  start_iso: string;
  end_iso: string;
  duration_seconds: number;
  events_count: number;
  frames_count: number;
}

export interface TypedText {
  ts_start: number;
  ts_end: number;
  app: string;
  field: string;
  text: string;
  confidence: number;
  ime_suspected?: boolean;
}

export interface Identifier {
  value: string;
  kind: 'case_id' | 'entity' | 'doc_no' | 'other';
  first_ts: number;
  last_ts: number;
  sources: string[];
}

export interface NormalizedEvent {
  event_id: string;
  session_id: string;
  chunk_id: string;
  timestamp_ms: number;
  timestamp_iso: string;
  layer: string;
  event_type: string;
  app_name: string;
  process_name: string;
  window_title: string;
  clean_title: string;
  title_template?: string;
  extracted_text?: string;
  typed_text?: string;
  extracted_case_ids: string[];
  screenshot_file?: string;
  payload_summary: string;
}

export interface Burst {
  burst_id: string;
  session_id: string;
  start_ms: number;
  start_iso: string;
  end_ms: number;
  end_iso: string;
  duration_ms: number;
  app_name: string;
  window_title: string;
  clean_title: string;
  title_template?: string;
  event_count: number;
  event_types: Record<string, number>;
  events?: Array<{
    event_id: string;
    event_type: string;
    timestamp_ms: number;
    app_name?: string;
  }>;
  typed_texts?: TypedText[];
  clipboard_changes?: Array<{
    timestamp_ms: number;
    text_length?: number;
  }>;
  titles?: string[];
  typed_text?: string;
  extracted_text?: string;
  case_ids: string[];
  before_frame?: Frame | null;
  after_frame?: Frame | null;
  gap_before_s?: number;
  dwell_s?: number;
  event_rate?: number;
  screenshot_file?: string;
  has_screenshot: boolean;
  input_mode: InputMode;
  signature: string;
}

export interface GroundedBurst extends Burst {
  semantic_action: string;
  ui_target: string;
  intent: string;
  grounding_mode: 'mock' | 'vision' | 'ocr_text' | 'rule';
}

export interface Activity {
  activity_id: string;
  session_id: string;
  start_ms: number;
  start_iso: string;
  end_ms: number;
  end_iso: string;
  burst_ids: string[];
  semantic_action_ids: string[];
  summary: string;
  app_names: string[];
  case_ids: string[];
  provisional_label: string;
}

export interface TaskThreadRoot {
  canonical_root_id: string;
  label: string;
  objective: string;
  deliverable: string;
  success_criteria: string;
  summary: string;
  family_anchors: string[];
  case_anchors: string[];
  activity_ids: string[];
  burst_ids: string[];
  observed_apps: string[];
  event_count: number;
}

export interface ExecutionSegment {
  session_id: string;
  start: string; // ISO 8601 UTC string
  end: string;   // ISO 8601 UTC string
  label: string;
}

export interface CanonicalExecution {
  exec_id: string;
  code: string;
  family_name: string;
  variant?: string | null;
  case_id: string;
  start_iso: string;
  end_iso: string;
  start_ms: number;
  end_ms: number;
  apps: string[];
  continues_from_prev?: boolean;
  continues_to_next?: boolean;
  split_id?: string | null;
  phase?: number;
  seq?: number;
}
