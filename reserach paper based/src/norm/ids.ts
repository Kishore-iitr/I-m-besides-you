import { Identifier } from '../types.js';

export interface RawTextSource {
  text: string;
  source: string; // e.g. 'window_title', 'extracted_text', 'typed_text'
  timestamp_ms: number;
}

/**
 * Discover and extract identifiers across multiple sources.
 * Emits Identifier { value, kind, first_ts, last_ts, sources }.
 */
export function extractGenericIdentifiers(sources: RawTextSource[]): Identifier[] {
  const identifierMap = new Map<string, {
    kind: 'case_id' | 'entity' | 'doc_no' | 'other';
    first_ts: number;
    last_ts: number;
    sources: Set<string>;
    count: number;
  }>();

  // Pattern A: Generic alphanumeric case/order/batch IDs: [A-Z]{1,6}[-_]?\d{3,}(-\d+)*
  const caseIdRegex = /\b([A-Z]{1,6}[-_]?\d{3,}(?:[-_]\d+)*)\b/g;

  // Pattern B: Long standalone digit strings (>= 6 digits), e.g. barcode, tax ID, slip number
  const docNoRegex = /\b(\d{6,})\b/g;

  // Pattern C: Japanese company entity candidates ending with 株式会社, (株), （株）
  const companyRegex = /(?:株式会社\s*[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}A-Za-z0-9]+|[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}A-Za-z0-9]+\s*(?:株式会社|\(株\)|（株）))/gu;

  // Pattern D: Japanese person/staff names near 様, 氏, 担当, 殿
  const personRegex = /([\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}]{2,6})\s*(?:様|氏|担当|殿)/gu;

  // Pattern E: Quoted strings that might be entity names
  const quotedRegex = /[「"']([^「"'」\r\n]{3,25})[」"']/g;

  for (const item of sources) {
    if (!item.text) continue;
    const text = item.text;
    const ts = item.timestamp_ms;
    const srcName = item.source;

    // Helper to record candidate
    function record(val: string, kind: 'case_id' | 'entity' | 'doc_no' | 'other') {
      const trimmed = val.trim();
      if (!trimmed || trimmed.length < 3) return;

      if (!identifierMap.has(trimmed)) {
        identifierMap.set(trimmed, {
          kind,
          first_ts: ts,
          last_ts: ts,
          sources: new Set([srcName]),
          count: 1,
        });
      } else {
        const entry = identifierMap.get(trimmed)!;
        entry.first_ts = Math.min(entry.first_ts, ts);
        entry.last_ts = Math.max(entry.last_ts, ts);
        entry.sources.add(srcName);
        entry.count++;
      }
    }

    // 1. Case IDs
    caseIdRegex.lastIndex = 0;
    let mCase: RegExpExecArray | null;
    while ((mCase = caseIdRegex.exec(text)) !== null) {
      // Ignore common false positives like HTML color codes or standard ISO date parts
      const val = mCase[1];
      if (/^(TRUE|FALSE|NULL|HTTP|HTTPS|UTF8|JSON|PAGE|NODE)$/i.test(val)) continue;
      record(val, 'case_id');
    }

    // 2. Doc Numbers
    docNoRegex.lastIndex = 0;
    let mDoc: RegExpExecArray | null;
    while ((mDoc = docNoRegex.exec(text)) !== null) {
      const val = mDoc[1];
      // Skip if already part of an alphanumeric case ID
      record(val, 'doc_no');
    }

    // 3. Japanese company names
    companyRegex.lastIndex = 0;
    let mComp: RegExpExecArray | null;
    while ((mComp = companyRegex.exec(text)) !== null) {
      record(mComp[0], 'entity');
    }

    // 4. Japanese person names
    personRegex.lastIndex = 0;
    let mPerson: RegExpExecArray | null;
    while ((mPerson = personRegex.exec(text)) !== null) {
      record(mPerson[1], 'entity');
    }

    // 5. Quoted entity names
    quotedRegex.lastIndex = 0;
    let mQuote: RegExpExecArray | null;
    while ((mQuote = quotedRegex.exec(text)) !== null) {
      const val = mQuote[1].trim();
      // Only keep if looks like a name or title, not code
      if (!/[{}[\];=]/.test(val) && val.length >= 3) {
        record(val, 'other');
      }
    }
  }

  // Convert map to sorted Identifier array
  const identifiers: Identifier[] = Array.from(identifierMap.entries())
    .map(([value, info]) => ({
      value,
      kind: info.kind,
      first_ts: info.first_ts,
      last_ts: info.last_ts,
      sources: Array.from(info.sources).sort(),
    }))
    .sort((a, b) => a.first_ts - b.first_ts || a.value.localeCompare(b.value));

  return identifiers;
}

/**
 * Discover dominant ID formats dynamically from data (e.g. `[A-Z]{2,4}-\d{6}-\d{3}`).
 * Replaces digits with \d+ and letters with [A-Z]+ to deduce templates.
 */
export function discoverIdFormats(identifiers: Identifier[]): Array<{ format: string; count: number; examples: string[] }> {
  const formatCounts = new Map<string, { count: number; examples: Set<string> }>();

  for (const id of identifiers) {
    if (id.kind !== 'case_id' && id.kind !== 'doc_no') continue;

    // Convert value into abstract pattern
    const pattern = id.value
      .replace(/[A-Z]+/g, m => `[A-Z]{${m.length}}`)
      .replace(/\d+/g, m => `\\d{${m.length}}`);

    if (!formatCounts.has(pattern)) {
      formatCounts.set(pattern, { count: 1, examples: new Set([id.value]) });
    } else {
      const entry = formatCounts.get(pattern)!;
      entry.count++;
      if (entry.examples.size < 3) entry.examples.add(id.value);
    }
  }

  return Array.from(formatCounts.entries())
    .map(([format, data]) => ({
      format,
      count: data.count,
      examples: Array.from(data.examples),
    }))
    .sort((a, b) => b.count - a.count);
}

/**
 * Fast helper for extracting case IDs from string list using generic discovery
 */
export function extractIdentifiers(
  texts: (string | undefined | null)[],
  fallbackPatterns?: string[]
): string[] {
  const found = new Set<string>();

  // 1. Generic case ID pattern: [A-Z]{1,6}[-_]?\d{3,}(-\d+)*
  const genericRegex = /\b([A-Z]{1,6}[-_]?\d{3,}(?:[-_]\d+)*)\b/g;

  for (const text of texts) {
    if (!text) continue;
    genericRegex.lastIndex = 0;
    let match: RegExpExecArray | null;
    while ((match = genericRegex.exec(text)) !== null) {
      const val = match[1];
      if (!/^(TRUE|FALSE|NULL|HTTP|HTTPS|UTF8|JSON|PAGE|NODE)$/i.test(val)) {
        found.add(val);
      }
    }
  }

  // 2. If fallback patterns provided, check them too
  if (fallbackPatterns && fallbackPatterns.length > 0) {
    for (const pat of fallbackPatterns) {
      try {
        const regex = new RegExp(pat, 'g');
        for (const text of texts) {
          if (!text) continue;
          regex.lastIndex = 0;
          let match: RegExpExecArray | null;
          while ((match = regex.exec(text)) !== null) {
            if (match[0]) found.add(match[0]);
          }
        }
      } catch {
        // Ignore invalid regex
      }
    }
  }

  return Array.from(found).sort();
}

export function redactText(text: string | undefined | null, enabled: boolean): string {
  if (!text) return '';
  if (!enabled) return text;

  // Mask digit sequences >= 4 digits
  let redacted = text.replace(/\b\d{4,}\b/g, '[REDACTED_NUM]');
  return redacted;
}
