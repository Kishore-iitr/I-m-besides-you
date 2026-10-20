import { RawEvent } from '../types.js';
import { SessionInfo } from '../io/loader.js';
import { readJSONL } from '../io/jsonl.js';
import { ClockAlignmentReport } from '../schemas/gt.js';

export async function measureClockAlignment(
  sessionInfo: SessionInfo,
  rawEvents: RawEvent[]
): Promise<ClockAlignmentReport> {
  if (!sessionInfo.hasGt || !sessionInfo.gtPath) {
    return {
      sessionId: sessionInfo.sessionId,
      hasGroundTruth: false,
      estimatedOffsetMs: 0,
      confidence: 'unaligned',
      evidence: [],
      medianOffsetMs: 0,
      p90OffsetMs: 0,
    };
  }

  const gtLines = await readJSONL<any>(sessionInfo.gtPath);
  const evidence: Array<{
    eventType: string;
    gtIso: string;
    eventIso: string;
    offsetMs: number;
    matchedOn: string;
  }> = [];

  // Match process_started with closest app_switch or title change
  const appSwitches = rawEvents.filter(e => e.event_type === 'app_switch' || e.event_type === 'window_title_change');

  for (const gt of gtLines) {
    if (gt.event === 'process_started') {
      const gtMs = Date.parse(gt.ts_utc);
      const procCode = gt.process_code || '';
      const procName = gt.process_name || '';

      // Find closest app switch within 15 seconds
      let bestEvent: RawEvent | null = null;
      let minDiff = 15000;

      for (const ev of appSwitches) {
        const diff = Math.abs(ev.timestamp_ms - gtMs);
        if (diff < minDiff) {
          // Check if window title or app has keywords
          const title = (ev.context?.active_app?.window_title || ev.payload?.new_app?.window_title || '');
          if (title.includes(procName) || title.includes('Chrome') || title.includes('Excel') || title.includes('Notepad')) {
            minDiff = diff;
            bestEvent = ev;
          }
        }
      }

      if (bestEvent) {
        const offset = bestEvent.timestamp_ms - gtMs;
        evidence.push({
          eventType: 'process_started',
          gtIso: gt.ts_utc,
          eventIso: bestEvent.timestamp_iso,
          offsetMs: offset,
          matchedOn: `proc=${procCode} app=${bestEvent.payload?.new_app?.app_name || 'app'}`,
        });
      }
    }
  }

  if (evidence.length === 0) {
    return {
      sessionId: sessionInfo.sessionId,
      hasGroundTruth: true,
      estimatedOffsetMs: 0,
      confidence: 'low',
      evidence: [],
      medianOffsetMs: 0,
      p90OffsetMs: 0,
    };
  }

  // Calculate median offset
  const sortedOffsets = evidence.map(e => e.offsetMs).sort((a, b) => a - b);
  const medianOffsetMs = sortedOffsets[Math.floor(sortedOffsets.length / 2)];
  const p90Index = Math.floor(sortedOffsets.length * 0.9);
  const p90OffsetMs = sortedOffsets[p90Index];

  // If standard deviation or IQR is small, high confidence
  const absOffsets = sortedOffsets.map(o => Math.abs(o - medianOffsetMs));
  const medianAbsDev = absOffsets.sort((a, b) => a - b)[Math.floor(absOffsets.length / 2)];

  let confidence: 'high' | 'medium' | 'low' = 'low';
  if (evidence.length >= 5 && medianAbsDev <= 3000) {
    confidence = 'high';
  } else if (evidence.length >= 2 && medianAbsDev <= 8000) {
    confidence = 'medium';
  }

  return {
    sessionId: sessionInfo.sessionId,
    hasGroundTruth: true,
    estimatedOffsetMs: medianOffsetMs,
    confidence,
    evidence: evidence.slice(0, 15), // top 15 evidence records
    medianOffsetMs,
    p90OffsetMs,
  };
}
