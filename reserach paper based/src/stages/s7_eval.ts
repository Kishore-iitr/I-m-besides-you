import path from 'node:path';
import { DatasetName, ExecutionSegment } from '../types.js';
import { readJSON, readJSONL, writeJSONAtomic } from '../io/jsonl.js';
import { CanonicalGtFile } from '../schemas/gt.js';
import { NormalizedEvent } from '../schemas/norm.js';
import { EvaluationReport, EvaluationReportSchema } from '../schemas/eval.js';
import { runEvaluation } from '../eval/metrics.js';

export async function runS7Eval(
  sessionId: string,
  dataset: DatasetName,
  projectRoot: string = process.cwd()
): Promise<EvaluationReport> {
  const artifactsDir = path.join(projectRoot, 'artifacts', dataset, sessionId);
  const segmentsPath = path.join(artifactsDir, 'segments.jsonl');
  const gtPath = path.join(artifactsDir, 's2_canonical_gt.json');
  const normPath = path.join(artifactsDir, 's1_normalized.jsonl');

  const segments = await readJSONL<ExecutionSegment>(segmentsPath);
  const canonicalGt = readJSON<CanonicalGtFile>(gtPath);
  const normEvents = await readJSONL<NormalizedEvent>(normPath);

  if (segments.length === 0) {
    throw new Error(`No segments found in ${segmentsPath}`);
  }
  if (!canonicalGt || canonicalGt.executions.length === 0) {
    throw new Error(`No ground truth found in ${gtPath}`);
  }

  const report = runEvaluation(
    sessionId,
    segments,
    canonicalGt.executions,
    normEvents,
    [15, 30, 60]
  );

  EvaluationReportSchema.parse(report);

  const outPath = path.join(artifactsDir, 's7_evaluation.json');
  writeJSONAtomic(outPath, report);

  return report;
}
