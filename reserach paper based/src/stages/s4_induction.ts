import path from 'node:path';
import { DatasetName, Activity } from '../types.js';
import { loadAppEnv } from '../config.js';
import { readJSONL, writeJSONL } from '../io/jsonl.js';
import { LlmClient } from '../llm/client.js';
import { ActivitySchema } from '../schemas/activities.js';
import { GroundedBurst } from '../schemas/grounding.js';

export async function runS4Induction(
  sessionId: string,
  dataset: DatasetName,
  projectRoot: string = process.cwd(),
  forceMock: boolean = true
): Promise<{ activitiesCount: number }> {
  const artifactsDir = path.join(projectRoot, 'artifacts', dataset, sessionId);
  const groundedPath = path.join(artifactsDir, 's3_grounded.jsonl');

  const groundedBursts = await readJSONL<GroundedBurst>(groundedPath);
  if (groundedBursts.length === 0) {
    throw new Error(`No grounded bursts found in ${groundedPath}. Did S3 run?`);
  }

  const env = loadAppEnv();
  const llmClient = new LlmClient(env, projectRoot);

  const activities = llmClient.mock.induceActivities(groundedBursts);

  for (const act of activities) {
    ActivitySchema.parse(act);
  }

  const outPath = path.join(artifactsDir, 's4_activities.jsonl');
  await writeJSONL(outPath, activities);

  return {
    activitiesCount: activities.length,
  };
}
