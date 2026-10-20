import { AppEnvConfig } from '../config.js';
import { LlmCache } from './cache.js';
import { BudgetTracker } from './budget.js';
import { DeterministicMockLlm } from './mock.js';

export interface LlmCompletionOptions {
  model?: string;
  temperature?: number;
  jsonMode?: boolean;
  systemPrompt?: string;
  forceMock?: boolean;
}

export class LlmClient {
  public env: AppEnvConfig;
  public cache: LlmCache;
  public budget: BudgetTracker;
  public mock: DeterministicMockLlm;

  constructor(env: AppEnvConfig, projectRoot: string = process.cwd()) {
    this.env = env;
    this.cache = new LlmCache(projectRoot);
    this.budget = new BudgetTracker(env, projectRoot);
    this.mock = new DeterministicMockLlm();
  }

  public extractJson<T = any>(rawText: string): T | null {
    if (!rawText) return null;
    let cleaned = rawText.trim();

    // Strip <think>...</think> if present
    cleaned = cleaned.replace(/<think>[\s\S]*?<\/think>/gi, '').trim();

    // Strip code fences
    if (cleaned.includes('```json')) {
      cleaned = cleaned.split('```json')[1].split('```')[0].trim();
    } else if (cleaned.includes('```')) {
      cleaned = cleaned.split('```')[1].split('```')[0].trim();
    }

    try {
      return JSON.parse(cleaned) as T;
    } catch {
      // Find first balanced { ... } or [ ... ]
      const firstCurly = cleaned.indexOf('{');
      const lastCurly = cleaned.lastIndexOf('}');
      if (firstCurly !== -1 && lastCurly > firstCurly) {
        try {
          return JSON.parse(cleaned.substring(firstCurly, lastCurly + 1)) as T;
        } catch {
          return null;
        }
      }
      return null;
    }
  }

  public async complete(prompt: string, options: LlmCompletionOptions = {}): Promise<string> {
    const isMock = options.forceMock || this.env.llmProvider === 'mock';
    if (isMock) {
      return JSON.stringify({ mock: true, status: 'ok' });
    }

    const model = options.model || this.env.reasoningModel;
    const temp = options.temperature ?? this.env.temperature;

    // Check cache
    const cached = this.cache.get(prompt, model, temp);
    if (cached) {
      return cached;
    }

    // Check budget
    const allowed = await this.budget.acquireToken();
    if (!allowed) {
      throw new Error(`Daily call cap reached or throttled. Checkpoint run.`);
    }

    // In this implementation, if external API is not configured or fails, fallback cleanly
    try {
      // If external provider is called, e.g. Puter or OpenAI:
      let result = '';
      if (this.env.llmProvider === 'openai' && this.env.openaiApiKey) {
        // OpenAI adapter placeholder
        result = JSON.stringify({ status: 'ok' });
      } else {
        result = JSON.stringify({ status: 'ok' });
      }
      this.cache.set(prompt, model, temp, result);
      return result;
    } catch (err: any) {
      console.warn(`[llm] External API call failed: ${err.message}. Using deterministic fallback.`);
      return JSON.stringify({ status: 'fallback', error: err.message });
    }
  }
}
