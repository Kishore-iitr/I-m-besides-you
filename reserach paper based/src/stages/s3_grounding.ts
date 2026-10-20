import path from 'node:path';
import { DatasetName, GroundedBurst } from '../types.js';
import { loadAppEnv } from '../config.js';
import { readJSONL, writeJSONL } from '../io/jsonl.js';
import { LlmClient } from '../llm/client.js';
import { GroundedBurstSchema } from '../schemas/grounding.js';
import { Burst } from '../schemas/norm.js';

export async function runS3Grounding(
  sessionId: string,
  dataset: DatasetName,
  projectRoot: string = process.cwd(),
  forceMock: boolean = true
): Promise<{ groundedCount: number; uniqueSignaturesCount: number }> {
  const artifactsDir = path.join(projectRoot, 'artifacts', dataset, sessionId);
  const burstsPath = path.join(artifactsDir, 's1_bursts.jsonl');

  const bursts = await readJSONL<Burst>(burstsPath);
  if (bursts.length === 0) {
    throw new Error(`No bursts found in ${burstsPath}. Did S1 run?`);
  }

  const env = loadAppEnv();
  const llmClient = new LlmClient(env, projectRoot);

  // Signature cache to avoid grounding duplicate bursts
  const sigMap = new Map<string, { semantic_action: string; ui_target: string; intent: string }>();

  const groundedBursts: GroundedBurst[] = [];

  for (const b of bursts) {
    let actionInfo = sigMap.get(b.signature);
    if (!actionInfo) {
      actionInfo = llmClient.mock.groundBurst(b);
      sigMap.set(b.signature, actionInfo);
    }

    const grounded: GroundedBurst = {
      ...b,
      semantic_action: actionInfo.semantic_action,
      ui_target: actionInfo.ui_target,
      intent: actionInfo.intent,
      grounding_mode: 'mock',
    };

    GroundedBurstSchema.parse(grounded);
    groundedBursts.push(grounded);
  }

  const outPath = path.join(artifactsDir, 's3_grounded.jsonl');
  await writeJSONL(outPath, groundedBursts);

  return {
    groundedCount: groundedBursts.length,
    uniqueSignaturesCount: sigMap.size,
  };
}
