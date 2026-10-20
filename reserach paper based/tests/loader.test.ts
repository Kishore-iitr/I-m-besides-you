import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { inspectSession, loadAllRawEventsWithStats } from '../src/io/loader.js';
import { buildFrameList } from '../src/io/screenshots.js';
import { computeModeRegions } from '../src/stages/s0_preflight.js';
import { RawEvent } from '../src/types.js';

describe('S0 Tolerant Loader & Inventory Acceptance', () => {
  it('handles chunk with only screenshots, odd names, missing images, malformed lines, and duplicates', async () => {
    // Create temporary session directory
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'tmi-test-session-'));
    const sessionDir = path.join(tmpDir, 'ses_20260701-test');
    fs.mkdirSync(sessionDir, { recursive: true });

    // 1. Chunk with odd name and events + malformed line + duplicates
    const oddChunkDir = path.join(sessionDir, 'chunk_odd_name_999');
    fs.mkdirSync(oddChunkDir, { recursive: true });

    const rawLines = [
      JSON.stringify({
        event_id: 'ev_1',
        timestamp_ms: 1000000,
        event_type: 'mouse_click',
        layer: 'L1',
        payload: { target: 'button1' },
      }),
      // Malformed JSON line
      '{"event_id": "ev_bad", timestamp_ms: NOT_VALID_JSON',
      // Duplicate of ev_1
      JSON.stringify({
        event_id: 'ev_1',
        timestamp_ms: 1000000,
        event_type: 'mouse_click',
        layer: 'L1',
        payload: { target: 'button1' },
      }),
      // Screenshot event referencing a missing image
      JSON.stringify({
        event_id: 'ev_scr_missing',
        timestamp_ms: 1005000,
        event_type: 'screenshot_smart',
        layer: 'L2',
        payload: { file_reference: { filename: 'scr_missing_image.jpg' } },
      }),
      // Another event with no event_id (fallback dedupe)
      JSON.stringify({
        timestamp_ms: 1010000,
        event_type: 'keystroke',
        layer: 'L1',
        payload: { key: 'a' },
      }),
      // Exact duplicate of event with no event_id
      JSON.stringify({
        timestamp_ms: 1010000,
        event_type: 'keystroke',
        layer: 'L1',
        payload: { key: 'a' },
      }),
    ];

    fs.writeFileSync(path.join(oddChunkDir, 'events.jsonl'), rawLines.join('\n'), 'utf8');

    // 2. Chunk with ONLY screenshots (no events, no manifest)
    const screensOnlyChunk = path.join(sessionDir, 'chunk_screenshots_only');
    const screenshotsDir = path.join(screensOnlyChunk, 'screenshots');
    fs.mkdirSync(screenshotsDir, { recursive: true });

    // Create a dummy image file
    const realImgPath = path.join(screenshotsDir, 'scr_smart_1020000_monitor_1.jpg');
    fs.writeFileSync(realImgPath, Buffer.from([0xff, 0xd8, 0xff, 0xe0])); // JPEG header

    // Mock session info
    const sessionInfo = {
      sessionId: 'ses_20260701-test',
      sessionDir,
      dataset: 'A' as const,
      chunks: [
        {
          chunkDirName: 'chunk_odd_name_999',
          chunkPath: oddChunkDir,
          hasEvents: true,
          eventsPath: path.join(oddChunkDir, 'events.jsonl'),
          hasManifest: false,
          hasScreenshots: false,
          screenshotFiles: [],
        },
        {
          chunkDirName: 'chunk_screenshots_only',
          chunkPath: screensOnlyChunk,
          hasEvents: false,
          hasManifest: false,
          hasScreenshots: true,
          screenshotsDir,
          screenshotFiles: ['scr_smart_1020000_monitor_1.jpg'],
        },
      ],
      hasGt: false,
      hasGtManifest: false,
      malformedLinesCount: 0,
    };

    // Load events
    const { events, malformedLinesCount } = await loadAllRawEventsWithStats(sessionInfo);

    // Assertions:
    // Malformed line was caught and counted
    expect(malformedLinesCount).toBe(1);
    // Duplicate ev_1 and duplicate keystroke were deduped
    // Valid events: ev_1, ev_scr_missing, keystroke -> 3 events
    expect(events.length).toBe(3);
    expect(events[0].event_id).toBe('ev_1');
    expect(events[1].event_id).toBe('ev_scr_missing');

    // Build frame list
    const frames = buildFrameList(sessionInfo, events);

    // Frame 1: from event referencing missing file (exists = false, source = 'event')
    const missingFrame = frames.find(f => f.filename === 'scr_missing_image.jpg');
    expect(missingFrame).toBeDefined();
    expect(missingFrame?.exists).toBe(false);
    expect(missingFrame?.source).toBe('event');

    // Frame 2: orphan from disk without an event (exists = true, source = 'folder')
    const diskFrame = frames.find(f => f.filename === 'scr_smart_1020000_monitor_1.jpg');
    expect(diskFrame).toBeDefined();
    expect(diskFrame?.exists).toBe(true);
    expect(diskFrame?.source).toBe('folder');
    expect(diskFrame?.timestamp_ms).toBe(1020000);

    // Mode regions sum to session duration
    const tMin = 1000000;
    const tMax = 1020000;
    const regions = computeModeRegions(tMin, tMax, events, frames, 5000);
    const sumDuration = regions.reduce((acc, r) => acc + r.duration_seconds, 0);
    const expectedDuration = (tMax - tMin) / 1000;
    expect(Math.abs(sumDuration - expectedDuration)).toBeLessThan(0.01);

    // Clean up temporary directory
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });
});
