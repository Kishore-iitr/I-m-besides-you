import path from 'node:path';
import { DatasetName, ExecutionSegment } from '../types.js';
import { readJSON, readJSONL } from '../io/jsonl.js';
import { CanonicalGtFile } from '../schemas/gt.js';

export async function printTimelineViz(
  sessionId: string,
  dataset: DatasetName,
  projectRoot: string = process.cwd()
): Promise<void> {
  const artifactsDir = path.join(projectRoot, 'artifacts', dataset, sessionId);
  const segmentsPath = path.join(artifactsDir, 'segments.jsonl');
  const gtPath = path.join(artifactsDir, 's2_canonical_gt.json');

  const segments = await readJSONL<ExecutionSegment>(segmentsPath);
  const canonicalGt = readJSON<CanonicalGtFile>(gtPath);

  console.log('\n================================================================');
  console.log(`   TIMELINE VISUALIZATION: ${sessionId}`);
  console.log('================================================================');
  console.log('\n[CANONICAL GROUND TRUTH EXECUTIONS]');
  for (const gt of canonicalGt.executions.slice(0, 10)) {
    console.log(`  [GT ${gt.code.padEnd(2)}] ${gt.start_iso.slice(11, 19)} -> ${gt.end_iso.slice(11, 19)} | ${gt.case_id.padEnd(16)} | ${gt.family_name}`);
  }
  if (canonicalGt.executions.length > 10) {
    console.log(`  ... and ${canonicalGt.executions.length - 10} more GT executions`);
  }

  console.log('\n[PREDICTED SEGMENTS]');
  for (const seg of segments.slice(0, 10)) {
    console.log(`  [PRED] ${seg.start.slice(11, 19)} -> ${seg.end.slice(11, 19)} | label: ${seg.label}`);
  }
  if (segments.length > 10) {
    console.log(`  ... and ${segments.length - 10} more predicted segments`);
  }
  console.log('================================================================\n');
}
