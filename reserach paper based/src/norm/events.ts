import { RawEvent, NormalizedEvent } from '../types.js';
import { DatasetConfig } from '../config.js';
import { cleanWindowTitle, templateWindowTitle } from './titles.js';
import { extractIdentifiers } from './ids.js';

export function normalizeRawEvents(
  rawEvents: RawEvent[],
  config: DatasetConfig
): NormalizedEvent[] {
  const normalized: NormalizedEvent[] = [];

  // Configurable recorder process filters
  const recorderPatterns = (
    config.recorder_process_patterns || [config.recorder_process || 'procmine', 'agent']
  ).map(p => p.toLowerCase());

  for (const ev of rawEvents) {
    const processName = (
      ev.context?.active_app?.process_name ||
      ev.payload?.new_app?.process_name ||
      ev.payload?.app_name ||
      ''
    ).trim();

    const lowerProc = processName.toLowerCase();

    // 1. Drop recorder events matching configured patterns (e.g. procmine-desktop-agent.exe)
    const isRecorder = recorderPatterns.some(pat => lowerProc.includes(pat));
    if (isRecorder) {
      continue;
    }

    // 2. Drop SYSTEM upload / extension events (keep session_start and session_end for bounds)
    const eventType = (ev.event_type || '').toLowerCase();
    const isSystemEvent = ev.layer === 'SYSTEM' || eventType.startsWith('system_');
    const isBoundEvent = eventType === 'session_start' || eventType === 'session_end';
    const isNoiseSystemEvent =
      (isSystemEvent && !isBoundEvent) ||
      eventType.includes('upload') ||
      eventType.includes('extension') ||
      eventType.includes('heartbeat');

    if (isNoiseSystemEvent) {
      continue;
    }

    const appName = (
      ev.context?.active_app?.app_name ||
      ev.payload?.new_app?.app_name ||
      processName.replace(/\.exe$/i, '') ||
      'unknown'
    ).trim();

    const windowTitle = (
      ev.context?.active_app?.window_title ||
      ev.payload?.new_app?.window_title ||
      ev.payload?.new_title ||
      ev.payload?.window_title ||
      ''
    ).trim();

    const cleanTitle = cleanWindowTitle(windowTitle);
    const titleTemplate = templateWindowTitle(windowTitle);

    const extractedText = ev.context?.extracted_text?.text || undefined;

    // Screenshot file reference if any
    let screenshotFile: string | undefined = undefined;
    if (ev.payload?.file_reference?.filename) {
      screenshotFile = ev.payload.file_reference.filename;
    }

    // Extract identifiers from windowTitle, cleanTitle, extractedText, and clipboard preview
    const clipboardPreview = ev.payload?.content_preview || ev.payload?.text_preview || undefined;
    const extractedCaseIds = extractIdentifiers(
      [windowTitle, cleanTitle, extractedText, clipboardPreview],
      config.case_id_patterns
    );

    let payloadSummary = '';
    if (ev.event_type === 'app_switch') {
      payloadSummary = `Switch to ${appName} [${cleanTitle}]`;
    } else if (ev.event_type === 'mouse_click') {
      const targetElem = ev.payload?.target_element?.class_name || ev.payload?.target_element?.control_type || '';
      payloadSummary = `Click ${targetElem} at (${ev.payload?.coordinates?.x ?? ''}, ${ev.payload?.coordinates?.y ?? ''})`;
    } else if (ev.event_type === 'keystroke') {
      payloadSummary = `Key ${ev.payload?.key || ''}`;
    } else if (ev.event_type === 'clipboard_change') {
      payloadSummary = `Clipboard change (len=${ev.payload?.text_length ?? 0})`;
    } else {
      payloadSummary = `${ev.event_type}`;
    }

    normalized.push({
      event_id: ev.event_id || `ev_${ev.timestamp_ms}_${normalized.length}`,
      session_id: ev.session_id || 'unknown',
      chunk_id: ev.correlation?.chunk_id || '',
      timestamp_ms: ev.timestamp_ms,
      timestamp_iso: ev.timestamp_iso || new Date(ev.timestamp_ms).toISOString(),
      layer: ev.layer || 'L1',
      event_type: ev.event_type,
      app_name: appName,
      process_name: processName,
      window_title: windowTitle,
      clean_title: cleanTitle,
      title_template: titleTemplate,
      extracted_text: extractedText,
      extracted_case_ids: extractedCaseIds,
      screenshot_file: screenshotFile,
      payload_summary: payloadSummary,
    });
  }

  return normalized;
}
