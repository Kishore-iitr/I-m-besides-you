import fs from 'node:fs';
import path from 'node:path';
import dotenv from 'dotenv';
import { DatasetName } from './types.js';

dotenv.config();

export interface DatasetConfig {
  dataset: DatasetName;
  recorder_process: string;
  recorder_process_patterns?: string[];
  idle_gap_threshold_ms: number;
  burst_idle_s?: number;
  keystroke_idle_threshold_ms: number;
  app_switch_collapse_ms?: number;
  burst_max_events: number;
  boundary_snap_tolerance_sec: number;
  eval_tolerance_sec: number[];
  case_id_patterns: string[];
  domain_whitelist: string[];
}

export interface AppEnvConfig {
  llmProvider: string;
  puterAuthToken?: string;
  puterTransport: string;
  openaiApiKey?: string;
  geminiApiKey?: string;
  anthropicApiKey?: string;
  groundingModel: string;
  reasoningModel: string;
  judgeModel: string;
  fallbackModels: string[];
  maxUsd: number;
  rpmLimit: number;
  dailyCallCap: number;
  maxPromptTokens: number;
  temperature: number;
  concurrency: number;
  redact: boolean;
}

export function loadDatasetConfig(dataset: DatasetName, projectRoot: string = process.cwd()): DatasetConfig {
  const filename = dataset.toLowerCase() === 'b' ? 'dataset_b.json' : 'dataset_a.json';
  const configPath = path.join(projectRoot, 'config', filename);
  if (!fs.existsSync(configPath)) {
    throw new Error(`Dataset config not found at: ${configPath}`);
  }
  const content = fs.readFileSync(configPath, 'utf8');
  return JSON.parse(content) as DatasetConfig;
}

export function loadAppEnv(): AppEnvConfig {
  return {
    llmProvider: process.env.LLM_PROVIDER || 'mock',
    puterAuthToken: process.env.PUTER_AUTH_TOKEN,
    puterTransport: process.env.PUTER_TRANSPORT || 'auto',
    openaiApiKey: process.env.OPENAI_API_KEY,
    geminiApiKey: process.env.GEMINI_API_KEY,
    anthropicApiKey: process.env.ANTHROPIC_API_KEY,
    groundingModel: process.env.GROUNDING_MODEL || 'mock-grounding',
    reasoningModel: process.env.REASONING_MODEL || 'mock-reasoning',
    judgeModel: process.env.JUDGE_MODEL || 'mock-judge',
    fallbackModels: (process.env.FALLBACK_MODELS || '').split(',').map(s => s.trim()).filter(Boolean),
    maxUsd: parseFloat(process.env.MAX_USD || '10.0'),
    rpmLimit: parseInt(process.env.RPM_LIMIT || '15', 10),
    dailyCallCap: parseInt(process.env.DAILY_CALL_CAP || '900', 10),
    maxPromptTokens: parseInt(process.env.MAX_PROMPT_TOKENS || '12000', 10),
    temperature: parseFloat(process.env.TEMPERATURE || '0.2'),
    concurrency: parseInt(process.env.CONCURRENCY || '2', 10),
    redact: process.env.REDACT === 'true',
  };
}
