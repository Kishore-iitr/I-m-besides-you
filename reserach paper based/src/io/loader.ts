import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { DatasetName, RawEvent } from '../types.js';
import { readJSON } from './jsonl.js';

export interface ChunkInfo {
  chunkDirName: string;
  chunkPath: string;
  hasEvents: boolean;
  eventsPath?: string;
  hasManifest: boolean;
  manifestPath?: string;
  manifestData?: any;
  hasScreenshots: boolean;
  screenshotsDir?: string;
  screenshotFiles: string[];
}

export interface SessionInfo {
  sessionId: string;
  sessionDir: string;
  dataset: DatasetName;
  chunks: ChunkInfo[];
  hasGt: boolean;
  gtPath?: string;
  hasGtManifest: boolean;
  gtManifestPath?: string;
  gtManifestData?: any;
  malformedLinesCount: number;
}

export function findDatasetDir(dataset: DatasetName, projectRoot: string = process.cwd()): string {
  const dirName = dataset.toLowerCase() === 'b' ? 'dataset_b' : 'dataset_a';
  const candidate1 = path.join(projectRoot, dirName);
  if (fs.existsSync(candidate1)) return candidate1;

  const candidate2 = path.join(projectRoot, 'data', dirName);
  if (fs.existsSync(candidate2)) return candidate2;

  return candidate1;
}

export function listSessions(dataset: DatasetName, projectRoot: string = process.cwd()): string[] {
  const datasetDir = findDatasetDir(dataset, projectRoot);
  if (!fs.existsSync(datasetDir)) return [];
  try {
    const entries = fs.readdirSync(datasetDir, { withFileTypes: true });
    return entries
      .filter(e => e.isDirectory() && e.name.startsWith('ses_'))
      .map(e => e.name)
      .sort();
  } catch (err) {
    return [];
  }
}

/**
 * Recursively find all subdirectories that contain chunks, events, manifests, or screenshots.
 */
function walkSubdirsForChunks(dir: string, baseSessionDir: string): ChunkInfo[] {
  const chunks: ChunkInfo[] = [];

  function walk(currentDir: string) {
    let entries: fs.Dirent[] = [];
    try {
      entries = fs.readdirSync(currentDir, { withFileTypes: true });
    } catch {
      return;
    }

    const relName = path.relative(baseSessionDir, currentDir) || path.basename(currentDir);
    const eventsPath = path.join(currentDir, 'events.jsonl');
    const hasEvents = fs.existsSync(eventsPath);

    const manifestPath = path.join(currentDir, 'manifest.json');
    const hasManifest = fs.existsSync(manifestPath);
    let manifestData: any = undefined;
    if (hasManifest) {
      try {
        manifestData = readJSON(manifestPath);
      } catch {
        manifestData = undefined;
      }
    }

    const screenshotsDir = path.join(currentDir, 'screenshots');
    const hasScreenshots = fs.existsSync(screenshotsDir);
    let screenshotFiles: string[] = [];
    if (hasScreenshots) {
      try {
        screenshotFiles = fs.readdirSync(screenshotsDir)
          .filter(f => /\.(jpe?g|png|webp)$/i.test(f));
      } catch {
        screenshotFiles = [];
      }
    }

    // If this folder has events, manifest, or screenshots, record it as a chunk unit
    if (hasEvents || hasManifest || hasScreenshots || currentDir !== baseSessionDir) {
      if (hasEvents || hasManifest || hasScreenshots) {
        chunks.push({
          chunkDirName: relName.replace(/\\/g, '/'),
          chunkPath: currentDir,
          hasEvents,
          eventsPath: hasEvents ? eventsPath : undefined,
          hasManifest,
          manifestPath: hasManifest ? manifestPath : undefined,
          manifestData,
          hasScreenshots,
          screenshotsDir: hasScreenshots ? screenshotsDir : undefined,
          screenshotFiles,
        });
      }
    }

    // Recurse into subdirectories (skipping 'screenshots' directory itself)
    for (const entry of entries) {
      if (entry.isDirectory() && entry.name !== 'screenshots' && entry.name !== '.git') {
        walk(path.join(currentDir, entry.name));
      }
    }
  }

  walk(dir);
  return chunks;
}

export function inspectSession(
  sessionId: string,
  dataset: DatasetName,
  projectRoot: string = process.cwd()
): SessionInfo {
  const datasetDir = findDatasetDir(dataset, projectRoot);
  const sessionDir = path.join(datasetDir, sessionId);

  if (!fs.existsSync(sessionDir)) {
    throw new Error(`Session directory does not exist: ${sessionDir}`);
  }

  // Tolerant walker: collects every events.jsonl (any chunk name), screenshots/ dir, and manifest.json
  const chunks = walkSubdirsForChunks(sessionDir, sessionDir);

  // Sort chunks alphabetically/chronologically by chunkDirName
  chunks.sort((a, b) => a.chunkDirName.localeCompare(b.chunkDirName));

  const gtPath = path.join(sessionDir, 'gt.jsonl');
  const hasGt = fs.existsSync(gtPath);

  const gtManifestPath = path.join(sessionDir, 'gt_manifest.json');
  const hasGtManifest = fs.existsSync(gtManifestPath);
  let gtManifestData: any = undefined;
  if (hasGtManifest) {
    try {
      gtManifestData = readJSON(gtManifestPath);
    } catch {
      gtManifestData = undefined;
    }
  }

  return {
    sessionId,
    sessionDir,
    dataset,
    chunks,
    hasGt,
    gtPath: hasGt ? gtPath : undefined,
    hasGtManifest,
    gtManifestPath: hasGtManifest ? gtManifestPath : undefined,
    gtManifestData,
    malformedLinesCount: 0,
  };
}

export interface LoadEventsResult {
  events: RawEvent[];
  malformedLinesCount: number;
}

export async function loadAllRawEventsWithStats(
  sessionInfo: SessionInfo,
  limit?: number
): Promise<LoadEventsResult> {
  const rawEventsList: RawEvent[] = [];
  const seenEventKeys = new Set<string>();
  let malformedLinesCount = 0;

  for (const chunk of sessionInfo.chunks) {
    if (!chunk.hasEvents || !chunk.eventsPath) continue;

    let fileContent = '';
    try {
      fileContent = fs.readFileSync(chunk.eventsPath, 'utf8');
    } catch {
      continue;
    }

    const lines = fileContent.split(/\r?\n/);
    for (let lineNo = 0; lineNo < lines.length; lineNo++) {
      const line = lines[lineNo].trim();
      if (!line) continue;

      let parsed: any;
      try {
        parsed = JSON.parse(line);
      } catch (err) {
        malformedLinesCount++;
        continue;
      }

      if (!parsed || typeof parsed !== 'object') {
        malformedLinesCount++;
        continue;
      }

      // Ensure correlation chunk_id is present
      if (!parsed.correlation) {
        parsed.correlation = {};
      }
      if (!parsed.correlation.chunk_id) {
        parsed.correlation.chunk_id = chunk.chunkDirName;
      }

      // Deduplication key: event_id or fallback hash(ts + type + payload)
      let dedupeKey = parsed.event_id;
      if (!dedupeKey) {
        const payloadStr = JSON.stringify(parsed.payload || {});
        dedupeKey = crypto
          .createHash('sha256')
          .update(`${parsed.timestamp_ms}_${parsed.event_type}_${payloadStr}`)
          .digest('hex');
      }

      if (seenEventKeys.has(dedupeKey)) {
        // Skip duplicate
        continue;
      }
      seenEventKeys.add(dedupeKey);

      rawEventsList.push(parsed as RawEvent);
      if (limit && rawEventsList.length >= limit) {
        break;
      }
    }

    if (limit && rawEventsList.length >= limit) {
      break;
    }
  }

  // Deterministic sort: timestamp_ms ASC, then sequence_number ASC, then event_id ASC
  rawEventsList.sort((a, b) => {
    if (a.timestamp_ms !== b.timestamp_ms) {
      return a.timestamp_ms - b.timestamp_ms;
    }
    const seqA = a.correlation?.sequence_number ?? 0;
    const seqB = b.correlation?.sequence_number ?? 0;
    if (seqA !== seqB) {
      return seqA - seqB;
    }
    return (a.event_id || '').localeCompare(b.event_id || '');
  });

  return {
    events: rawEventsList,
    malformedLinesCount,
  };
}

export async function loadAllRawEvents(
  sessionInfo: SessionInfo,
  limit?: number
): Promise<RawEvent[]> {
  const result = await loadAllRawEventsWithStats(sessionInfo, limit);
  sessionInfo.malformedLinesCount = result.malformedLinesCount;
  return result.events;
}
