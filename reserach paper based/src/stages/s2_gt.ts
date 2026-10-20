import path from 'node:path';
import { DatasetName } from '../types.js';
import { inspectSession, loadAllRawEvents } from '../io/loader.js';
import { writeJSONAtomic } from '../io/jsonl.js';
import { buildCanonicalGt } from '../gt/build.js';
import { measureClockAlignment } from '../gt/align.js';
import { CanonicalGtFileSchema, ClockAlignmentReportSchema } from '../schemas/gt.js';

export async function runS2Gt(
  sessionId: string,
  dataset: DatasetName,
  projectRoot: string = process.cwd()
): Promise<{ executionsCount: number; alignmentOffsetMs: number }> {
  const sessionInfo = inspectSession(sessionId, dataset, projectRoot);
  const rawEvents = await loadAllRawEvents(sessionInfo);

  // 1. Build canonical ground truth
  const canonicalGt = await buildCanonicalGt(sessionInfo);
  CanonicalGtFileSchema.parse(canonicalGt);

  // 2. Measure clock alignment
  const alignmentReport = await measureClockAlignment(sessionInfo, rawEvents);
  ClockAlignmentReportSchema.parse(alignmentReport);

  const artifactsDir = path.join(projectRoot, 'artifacts', dataset, sessionId);
  const gtOutPath = path.join(artifactsDir, 's2_canonical_gt.json');
  const alignOutPath = path.join(artifactsDir, 's2_alignment.json');

  writeJSONAtomic(gtOutPath, canonicalGt);
  writeJSONAtomic(alignOutPath, alignmentReport);

  return {
    executionsCount: canonicalGt.executionsCount,
    alignmentOffsetMs: alignmentReport.estimatedOffsetMs,
  };
}
