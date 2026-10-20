import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

export class LlmCache {
  private cacheDir: string;

  constructor(projectRoot: string = process.cwd()) {
    this.cacheDir = path.join(projectRoot, '.cache', 'llm');
    if (!fs.existsSync(this.cacheDir)) {
      fs.mkdirSync(this.cacheDir, { recursive: true });
    }
  }

  private computeKey(prompt: string, model: string, temperature: number): string {
    const raw = `${model}:${temperature}:${prompt}`;
    return crypto.createHash('sha256').update(raw).digest('hex');
  }

  public get(prompt: string, model: string, temperature: number): string | null {
    const key = this.computeKey(prompt, model, temperature);
    const filePath = path.join(this.cacheDir, `${key}.json`);
    if (fs.existsSync(filePath)) {
      try {
        const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
        return data.response;
      } catch {
        return null;
      }
    }
    return null;
  }

  public set(prompt: string, model: string, temperature: number, response: string): void {
    const key = this.computeKey(prompt, model, temperature);
    const filePath = path.join(this.cacheDir, `${key}.json`);
    const tempPath = `${filePath}.tmp.${Date.now()}`;
    fs.writeFileSync(tempPath, JSON.stringify({ prompt, model, temperature, response, cachedAt: new Date().toISOString() }), 'utf8');
    fs.renameSync(tempPath, filePath);
  }
}
