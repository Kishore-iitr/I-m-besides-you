import path from 'node:path';
import { DatasetName } from '../types.js';
import { loadAppEnv } from '../config.js';
import { readJSONL, writeJSONAtomic } from '../io/jsonl.js';
import { LlmClient } from '../llm/client.js';
import { Activity } from '../schemas/activities.js';
import { TaskThreadsOutputSchema, TaskThreadsOutput } from '../schemas/taskThreads.js';

export async function runS5Clustering(
  sessionId: string,
  dataset: DatasetName,
  projectRoot: string = process.cwd(),
  forceMock: boolean = true
): Promise<{ rootsCount: number; assignmentsCount: number }> {
  const artifactsDir = path.join(projectRoot, 'artifacts', dataset, sessionId);
  const activitiesPath = path.join(artifactsDir, 's4_activities.jsonl');

  const activities = await readJSONL<Activity>(activitiesPath);
  if (activities.length === 0) {
    throw new Error(`No activities found in ${activitiesPath}. Did S4 run?`);
  }

  const env = loadAppEnv();
  const llmClient = new LlmClient(env, projectRoot);

  const clustered = llmClient.mock.clusterTaskThreads(activities);

  const output: TaskThreadsOutput = {
    sessionId,
    createdAt: new Date().toISOString(),
    roots: clustered.roots,
    assignments: clustered.assignments,
  };

  TaskThreadsOutputSchema.parse(output);

  const outPath = path.join(artifactsDir, 's5_task_threads.json');
  writeJSONAtomic(outPath, output);

  return {
    rootsCount: output.roots.length,
    assignmentsCount: output.assignments.length,
  };
}
