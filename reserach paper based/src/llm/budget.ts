import fs from 'node:fs';
import path from 'node:path';
import { AppEnvConfig } from '../config.js';

interface DailyUsageData {
  dateUtc: string;
  callsCount: number;
  totalTokens: number;
  estimatedUsd: number;
}

export class BudgetTracker {
  private usageFilePath: string;
  private rpmLimit: number;
  private dailyCap: number;
  private callTimestamps: number[] = [];

  constructor(env: AppEnvConfig, projectRoot: string = process.cwd()) {
    const cacheDir = path.join(projectRoot, '.cache');
    if (!fs.existsSync(cacheDir)) {
      fs.mkdirSync(cacheDir, { recursive: true });
    }
    this.usageFilePath = path.join(cacheDir, 'usage_day.json');
    this.rpmLimit = env.rpmLimit || 15;
    this.dailyCap = env.dailyCallCap || 900;
  }

  private getTodayUtc(): string {
    return new Date().toISOString().slice(0, 10);
  }

  private loadUsage(): DailyUsageData {
    const today = this.getTodayUtc();
    if (fs.existsSync(this.usageFilePath)) {
      try {
        const data = JSON.parse(fs.readFileSync(this.usageFilePath, 'utf8')) as DailyUsageData;
        if (data.dateUtc === today) {
          return data;
        }
      } catch {
        // ignore
      }
    }
    return { dateUtc: today, callsCount: 0, totalTokens: 0, estimatedUsd: 0 };
  }

  private saveUsage(data: DailyUsageData): void {
    const tempPath = `${this.usageFilePath}.tmp.${Date.now()}`;
    fs.writeFileSync(tempPath, JSON.stringify(data, null, 2), 'utf8');
    fs.renameSync(tempPath, this.usageFilePath);
  }

  public async acquireToken(): Promise<boolean> {
    const usage = this.loadUsage();
    if (usage.callsCount >= this.dailyCap) {
      console.warn(`[budget] Daily call cap (${this.dailyCap}) reached for today (${usage.dateUtc}). Exiting cleanly.`);
      return false;
    }

    // RPM check
    const now = Date.now();
    this.callTimestamps = this.callTimestamps.filter(t => now - t < 60000);
    if (this.callTimestamps.length >= this.rpmLimit) {
      const waitTimeMs = 60000 - (now - this.callTimestamps[0]) + 100;
      await new Promise(r => setTimeout(r, waitTimeMs));
    }

    this.callTimestamps.push(Date.now());
    usage.callsCount++;
    this.saveUsage(usage);
    return true;
  }

  public recordUsage(tokens: number, costUsd: number = 0): void {
    const usage = this.loadUsage();
    usage.totalTokens += tokens;
    usage.estimatedUsd += costUsd;
    this.saveUsage(usage);
  }

  public getStats(): DailyUsageData {
    return this.loadUsage();
  }
}
