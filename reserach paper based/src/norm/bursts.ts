import { NormalizedEvent, Burst, Frame, TypedText, InputMode } from '../types.js';
import { DatasetConfig } from '../config.js';
import { collapseAppSwitches } from './titles.js';

export function formBursts(
  events: NormalizedEvent[],
  config: DatasetConfig,
  frames: Frame[] = [],
  typedTexts: TypedText[] = []
): Burst[] {
  const idleGapMs = (config.burst_idle_s || 3.0) * 1000;
  const maxEvents = config.burst_max_events || 40;
  const maxFrameDistMs = 15000; // 15 seconds max frame proximity

  // 1. Collapse transient app switch ping-pongs first
  const { events: collapsedEvents } = collapseAppSwitches(
    events,
    config.app_switch_collapse_ms || 1500
  );

  const bursts: Burst[] = [];
  let currentEvents: NormalizedEvent[] = [];
  let lastBurstEndMs: number | null = null;

  function findNearestBeforeFrame(t0: number): Frame | null {
    let best: Frame | null = null;
    let minDiff = Infinity;
    for (const f of frames) {
      if (f.timestamp_ms <= t0) {
        const diff = t0 - f.timestamp_ms;
        if (diff <= maxFrameDistMs && diff < minDiff) {
          minDiff = diff;
          best = f;
        }
      }
    }
    return best;
  }

  function findNearestAfterFrame(t1: number): Frame | null {
    let best: Frame | null = null;
    let minDiff = Infinity;
    for (const f of frames) {
      if (f.timestamp_ms >= t1) {
        const diff = f.timestamp_ms - t1;
        if (diff <= maxFrameDistMs && diff < minDiff) {
          minDiff = diff;
          best = f;
        }
      }
    }
    return best;
  }

  function flushBurst() {
    if (currentEvents.length === 0) return;

    const first = currentEvents[0];
    const last = currentEvents[currentEvents.length - 1];
    const startMs = first.timestamp_ms;
    const endMs = last.timestamp_ms;
    const dwellSec = Number(Math.max(0, (endMs - startMs) / 1000).toFixed(3));
    const gapBeforeSec = lastBurstEndMs !== null
      ? Number(Math.max(0, (startMs - lastBurstEndMs) / 1000).toFixed(3))
      : 0;

    lastBurstEndMs = endMs;

    const burstIndex = bursts.length + 1;
    const burstId = `burst_${first.session_id}_${startMs}_${burstIndex}`;

    const eventTypes: Record<string, number> = {};
    const caseIdsSet = new Set<string>();
    const titlesSet = new Set<string>();
    let screenshotFile: string | undefined = undefined;
    let extractedTextCombined = '';

    const compactEvents: Array<{
      event_id: string;
      event_type: string;
      timestamp_ms: number;
      app_name?: string;
    }> = [];

    const clipboardChanges: Array<{
      timestamp_ms: number;
      text_length?: number;
    }> = [];

    for (const ev of currentEvents) {
      eventTypes[ev.event_type] = (eventTypes[ev.event_type] || 0) + 1;

      for (const id of ev.extracted_case_ids) {
        caseIdsSet.add(id);
      }
      if (ev.clean_title) {
        titlesSet.add(ev.clean_title);
      }
      if (ev.screenshot_file && !screenshotFile) {
        screenshotFile = ev.screenshot_file;
      }
      if (ev.extracted_text && !extractedTextCombined.includes(ev.extracted_text)) {
        if (extractedTextCombined) extractedTextCombined += '\n\n';
        extractedTextCombined += ev.extracted_text;
      }

      compactEvents.push({
        event_id: ev.event_id,
        event_type: ev.event_type,
        timestamp_ms: ev.timestamp_ms,
        app_name: ev.app_name,
      });

      if (ev.event_type === 'clipboard_change') {
        const len = (ev as any).payload?.text_length || (ev.payload_summary.match(/len=(\d+)/)?.[1] ? parseInt(ev.payload_summary.match(/len=(\d+)/)![1], 10) : undefined);
        clipboardChanges.push({
          timestamp_ms: ev.timestamp_ms,
          text_length: len,
        });
      }
    }

    // Dominant app
    const appCounts: Record<string, number> = {};
    for (const ev of currentEvents) {
      appCounts[ev.app_name] = (appCounts[ev.app_name] || 0) + 1;
    }
    const dominantApp = Object.entries(appCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || first.app_name || 'unknown';
    const dominantTitle = Array.from(titlesSet)[0] || first.clean_title || '';
    const titleTemplate = first.title_template || dominantTitle;

    // Attached frames
    const beforeFrame = findNearestBeforeFrame(startMs);
    const afterFrame = findNearestAfterFrame(endMs);

    const hasScreenshot = !!(screenshotFile || beforeFrame || afterFrame);
    const inputMode: InputMode = hasScreenshot ? 'events_and_screens' : 'events_only';

    // Typed texts matching burst timeframe
    const matchedTypedTexts = typedTexts.filter(
      t => t.ts_start >= startMs && t.ts_end <= endMs
    );
    const typedTextStr = matchedTypedTexts.map(t => t.text).join(' ').trim() || undefined;

    // Signature for deduplication in LLM grounding
    const topEvents = Object.entries(eventTypes)
      .sort((a, b) => b[1] - a[1])
      .map(([k, v]) => `${k}:${v}`)
      .slice(0, 3)
      .join(',');
    const caseIdSig = Array.from(caseIdsSet)[0] || '';
    const signature = `${dominantApp}|${titleTemplate}|${topEvents}|${caseIdSig}`;

    // Truncate extracted_text to 2,000 characters
    const truncatedExtracted = extractedTextCombined
      ? extractedTextCombined.slice(0, 2000)
      : undefined;

    const eventRate = dwellSec > 0
      ? Number((currentEvents.length / dwellSec).toFixed(2))
      : currentEvents.length;

    bursts.push({
      burst_id: burstId,
      session_id: first.session_id,
      start_ms: startMs,
      start_iso: first.timestamp_iso,
      end_ms: endMs,
      end_iso: last.timestamp_iso,
      duration_ms: Math.max(0, endMs - startMs),
      app_name: dominantApp,
      window_title: first.window_title,
      clean_title: dominantTitle,
      title_template: titleTemplate,
      event_count: currentEvents.length,
      event_types: eventTypes,
      events: compactEvents,
      typed_texts: matchedTypedTexts.length > 0 ? matchedTypedTexts : undefined,
      typed_text: typedTextStr,
      clipboard_changes: clipboardChanges.length > 0 ? clipboardChanges : undefined,
      titles: Array.from(titlesSet),
      extracted_text: truncatedExtracted,
      case_ids: Array.from(caseIdsSet).sort(),
      before_frame: beforeFrame,
      after_frame: afterFrame,
      gap_before_s: gapBeforeSec,
      dwell_s: dwellSec,
      event_rate: eventRate,
      screenshot_file: screenshotFile || beforeFrame?.filename || afterFrame?.filename,
      has_screenshot: hasScreenshot,
      input_mode: inputMode,
      signature,
    });

    currentEvents = [];
  }

  // Iterate collapsed events to form bursts
  for (let i = 0; i < collapsedEvents.length; i++) {
    const ev = collapsedEvents[i];

    if (currentEvents.length > 0) {
      const prev = currentEvents[currentEvents.length - 1];
      const timeDiff = ev.timestamp_ms - prev.timestamp_ms;

      // Splitting criteria:
      // (a) idle gap > burst_idle_s
      const isIdleGap = timeDiff > idleGapMs;
      // (b) app change to a different process after collapse
      const isAppChange = ev.app_name !== prev.app_name;
      // (c) max 40 events
      const isLengthExceeded = currentEvents.length >= maxEvents;
      // Frame boundary: if current event is a screenshot_smart
      const isScreenshotBoundary = ev.event_type === 'screenshot_smart';

      if (isIdleGap || isAppChange || isLengthExceeded || isScreenshotBoundary) {
        flushBurst();
      }
    }

    currentEvents.push(ev);
  }

  flushBurst();

  // 2. Handle screens-only intervals:
  // For each consecutive pair of frames where no events occurred, create a screens-only burst
  if (frames.length >= 2) {
    const sortedFrames = [...frames].sort((a, b) => a.timestamp_ms - b.timestamp_ms);
    const sessionId = events[0]?.session_id || 'unknown';

    for (let f = 0; f < sortedFrames.length - 1; f++) {
      const f1 = sortedFrames[f];
      const f2 = sortedFrames[f + 1];

      // Check if any event falls strictly between f1 and f2
      const hasEventsBetween = events.some(
        e => e.timestamp_ms >= f1.timestamp_ms && e.timestamp_ms <= f2.timestamp_ms
      );

      if (!hasEventsBetween && f2.timestamp_ms > f1.timestamp_ms + 1000) {
        // Screens-only burst
        const startMs = f1.timestamp_ms;
        const endMs = f2.timestamp_ms;
        const dwellSec = Number(((endMs - startMs) / 1000).toFixed(3));
        const bId = `burst_${sessionId}_${startMs}_scr_${f + 1}`;

        bursts.push({
          burst_id: bId,
          session_id: sessionId,
          start_ms: startMs,
          start_iso: f1.timestamp_iso,
          end_ms: endMs,
          end_iso: f2.timestamp_iso,
          duration_ms: endMs - startMs,
          app_name: 'screen_capture',
          window_title: 'Screen Capture Only',
          clean_title: 'Screen Capture Only',
          title_template: 'Screen Capture Only',
          event_count: 0,
          event_types: {},
          events: [],
          case_ids: [],
          before_frame: f1,
          after_frame: f2,
          gap_before_s: 0,
          dwell_s: dwellSec,
          event_rate: 0,
          screenshot_file: f1.filename,
          has_screenshot: true,
          input_mode: 'screens_only',
          signature: `screens_only|${f1.filename}->${f2.filename}`,
        });
      }
    }
  }

  // Sort bursts chronologically by start_ms
  bursts.sort((a, b) => a.start_ms - b.start_ms);

  return bursts;
}
