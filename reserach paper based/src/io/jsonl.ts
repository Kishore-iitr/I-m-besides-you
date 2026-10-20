import fs from 'node:fs';
import readline from 'node:readline';

export async function* streamJSONL<T = any>(filePath: string): AsyncGenerator<T, void, unknown> {
  if (!fs.existsSync(filePath)) {
    return;
  }
  const fileStream = fs.createReadStream(filePath, { encoding: 'utf8' });
  const rl = readline.createInterface({
    input: fileStream,
    crlfDelay: Infinity,
  });

  for await (const line of rl) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try {
      yield JSON.parse(trimmed) as T;
    } catch (err) {
      // Ignore corrupted lines or log if needed
    }
  }
}

export async function readJSONL<T = any>(filePath: string, limit?: number): Promise<T[]> {
  const items: T[] = [];
  for await (const item of streamJSONL<T>(filePath)) {
    items.push(item);
    if (limit && items.length >= limit) {
      break;
    }
  }
  return items;
}

export async function writeJSONL<T = any>(filePath: string, items: T[]): Promise<void> {
  const dir = filePath.substring(0, Math.max(filePath.lastIndexOf('/'), filePath.lastIndexOf('\\')));
  if (dir && !fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }

  const fileStream = fs.createWriteStream(filePath, { encoding: 'utf8' });
  for (const item of items) {
    fileStream.write(JSON.stringify(item) + '\n');
  }
  await new Promise<void>((resolve, reject) => {
    fileStream.end(() => resolve());
    fileStream.on('error', reject);
  });
}

export function writeJSONAtomic(filePath: string, data: any): void {
  const dir = filePath.substring(0, Math.max(filePath.lastIndexOf('/'), filePath.lastIndexOf('\\')));
  if (dir && !fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  const tempPath = `${filePath}.tmp.${Date.now()}`;
  fs.writeFileSync(tempPath, JSON.stringify(data, null, 2), 'utf8');
  fs.renameSync(tempPath, filePath);
}

export function readJSON<T = any>(filePath: string): T {
  const content = fs.readFileSync(filePath, 'utf8');
  return JSON.parse(content) as T;
}
