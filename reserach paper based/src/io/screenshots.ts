import fs from 'node:fs';
import path from 'node:path';
import { ChunkInfo, SessionInfo } from './loader.js';
import { RawEvent, Frame } from '../types.js';

export interface ScreenshotResolution {
  available: boolean;
  filePath?: string;
  filename?: string;
  fileSizeBytes?: number;
}

export function resolveScreenshot(
  filename: string | undefined | null,
  chunks: ChunkInfo[]
): ScreenshotResolution {
  if (!filename) {
    return { available: false };
  }

  for (const chunk of chunks) {
    if (!chunk.hasScreenshots || !chunk.screenshotsDir) continue;
    const candidatePath = path.join(chunk.screenshotsDir, filename);
    if (fs.existsSync(candidatePath)) {
      try {
        const stats = fs.statSync(candidatePath);
        return {
          available: true,
          filePath: candidatePath,
          filename,
          fileSizeBytes: stats.size,
        };
      } catch {
        // Continue searching
      }
    }
  }

  return {
    available: false,
    filename,
  };
}

export function parseScreenshotFilename(filename: string): { timestamp_ms: number; monitor?: number } | null {
  // Pattern 1: scr_smart_<ms>_monitor_<n>_...
  const match1 = filename.match(/scr_smart_(\d+)(?:_monitor_(\d+))?/i);
  if (match1) {
    const ts = parseInt(match1[1], 10);
    const monitor = match1[2] ? parseInt(match1[2], 10) : undefined;
    if (!isNaN(ts) && ts > 0) {
      return { timestamp_ms: ts, monitor };
    }
  }

  // Pattern 2: Any 13-digit epoch timestamp in the filename
  const match2 = filename.match(/(?:^|\D)(\d{13})(?:\D|$)/);
  if (match2) {
    const ts = parseInt(match2[1], 10);
    if (!isNaN(ts) && ts > 0) {
      return { timestamp_ms: ts };
    }
  }

  return null;
}

/**
 * Build unified frame list from both screenshot_smart events and directory listing.
 */
export function buildFrameList(sessionInfo: SessionInfo, rawEvents: RawEvent[]): Frame[] {
  const framesMap = new Map<string, Frame>();
  const eventSeenFilenames = new Set<string>();

  // 1. Process screenshot_smart events first (file_reference prioritized)
  for (const ev of rawEvents) {
    if (ev.event_type !== 'screenshot_smart') continue;

    const fileRef = ev.payload?.file_reference;
    const filename = fileRef?.filename;
    if (!filename) continue;

    eventSeenFilenames.add(filename);
    const res = resolveScreenshot(filename, sessionInfo.chunks);

    const frame: Frame = {
      timestamp_ms: ev.timestamp_ms,
      timestamp_iso: ev.timestamp_iso || new Date(ev.timestamp_ms).toISOString(),
      filename,
      path: res.filePath || filename,
      exists: res.available,
      source: 'event',
      event_id: ev.event_id,
    };

    const parsed = parseScreenshotFilename(filename);
    if (parsed?.monitor !== undefined) {
      frame.monitor = parsed.monitor;
    }

    framesMap.set(filename, frame);
  }

  // 2. Discover frames physically present in screenshot directories (catch orphan frames)
  for (const chunk of sessionInfo.chunks) {
    if (!chunk.hasScreenshots || !chunk.screenshotsDir) continue;

    for (const filename of chunk.screenshotFiles) {
      if (framesMap.has(filename)) {
        // Already registered via event
        continue;
      }

      const filePath = path.join(chunk.screenshotsDir, filename);
      const parsed = parseScreenshotFilename(filename);

      let timestampMs: number;
      if (parsed) {
        timestampMs = parsed.timestamp_ms;
      } else {
        try {
          const stats = fs.statSync(filePath);
          timestampMs = stats.mtimeMs;
        } catch {
          timestampMs = 0;
        }
      }

      const frame: Frame = {
        timestamp_ms: timestampMs,
        timestamp_iso: new Date(timestampMs).toISOString(),
        filename,
        path: filePath,
        exists: true,
        source: 'folder',
      };

      if (parsed?.monitor !== undefined) {
        frame.monitor = parsed.monitor;
      }

      framesMap.set(filename, frame);
    }
  }

  // Convert to array and sort strictly by timestamp_ms ASC, then filename
  const frames = Array.from(framesMap.values());
  frames.sort((a, b) => {
    if (a.timestamp_ms !== b.timestamp_ms) {
      return a.timestamp_ms - b.timestamp_ms;
    }
    return a.filename.localeCompare(b.filename);
  });

  return frames;
}

export function readScreenshotBase64(filePath: string, redact: boolean = false): string | null {
  if (redact) {
    return null;
  }
  if (!fs.existsSync(filePath)) {
    return null;
  }
  try {
    const buffer = fs.readFileSync(filePath);
    return `data:image/jpeg;base64,${buffer.toString('base64')}`;
  } catch {
    return null;
  }
}
