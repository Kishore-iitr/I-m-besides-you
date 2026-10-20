export function cleanWindowTitle(title: string | undefined | null): string {
  if (!title) return '';

  let cleaned = title.trim();

  // Strip common application suffix patterns
  cleaned = cleaned.replace(/\s*-\s*Google Chrome$/i, '');
  cleaned = cleaned.replace(/\s*-\s*Microsoft Edge$/i, '');
  cleaned = cleaned.replace(/\s*-\s*Excel$/i, '');
  cleaned = cleaned.replace(/\s*-\s*Notepad$/i, '');
  cleaned = cleaned.replace(/\s*-\s*Word$/i, '');
  cleaned = cleaned.replace(/\s*-\s*PowerPoint$/i, '');
  cleaned = cleaned.replace(/\s*-\s*File Explorer$/i, '');
  cleaned = cleaned.replace(/\s*-\s*Windows PowerShell$/i, '');

  // Strip leading asterisks for modified files
  cleaned = cleaned.replace(/^\*\s*/, '');

  return cleaned.trim();
}

/**
 * Window-title templating: replace dates, times, case IDs, and long digit strings
 * with placeholder tokens to form a stable structural template.
 */
export function templateWindowTitle(title: string | undefined | null): string {
  if (!title) return '';

  let t = cleanWindowTitle(title);

  // Replace dates (YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD)
  t = t.replace(/\b\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\b/g, '<DATE>');

  // Replace times (HH:MM:SS or HH:MM)
  t = t.replace(/\b\d{1,2}:\d{2}(?::\d{2})?\b/g, '<TIME>');

  // Replace case / invoice / order IDs like ORD-182807-001, INV-110635-001, BATCH-123
  t = t.replace(/\b[A-Z]{1,6}[-_]?\d{3,}(?:[-_]\d+)*\b/g, '<ID>');

  // Replace long standalone numbers (>= 4 digits)
  t = t.replace(/\b\d{4,}\b/g, '<NUM>');

  // Replace hex strings / GUID-like sequences
  t = t.replace(/\b[0-9a-fA-F]{8,}\b/g, '<HEX>');

  return t.trim();
}

/**
 * App-switch collapsing: merge ping-pong sequences A -> B -> A within collapseMs (e.g. 1500ms)
 * and return the collapsed event list along with count of collapsed ping-pongs.
 */
export function collapseAppSwitches<T extends { event_type: string; app_name: string; timestamp_ms: number }>(
  events: T[],
  collapseMs: number = 1500
): { events: T[]; collapsedCount: number } {
  if (events.length < 3) {
    return { events: [...events], collapsedCount: 0 };
  }

  const result: T[] = [];
  let collapsedCount = 0;
  let i = 0;

  while (i < events.length) {
    const cur = events[i];

    // Check if cur is an app_switch
    if (cur.event_type === 'app_switch' && result.length > 0) {
      const prev = result[result.length - 1];
      const prevApp = prev.app_name;
      const transientApp = cur.app_name;

      // Look ahead for return switch back to prevApp within collapseMs
      let nextSwitchIdx = -1;
      for (let j = i + 1; j < events.length; j++) {
        const timeDiff = events[j].timestamp_ms - cur.timestamp_ms;
        if (timeDiff > collapseMs) break;

        if (events[j].event_type === 'app_switch') {
          if (events[j].app_name === prevApp) {
            nextSwitchIdx = j;
          }
          break;
        }
      }

      if (nextSwitchIdx !== -1 && transientApp !== prevApp) {
        // Ping-pong sequence detected: prevApp -> transientApp -> prevApp within collapseMs
        collapsedCount++;
        // Re-label any events between i and nextSwitchIdx to prevApp or skip transient switch
        for (let k = i; k <= nextSwitchIdx; k++) {
          if (events[k].event_type === 'app_switch') {
            // Drop redundant switch back and forth
            continue;
          }
          result.push({
            ...events[k],
            app_name: prevApp,
          });
        }
        i = nextSwitchIdx + 1;
        continue;
      }
    }

    result.push(cur);
    i++;
  }

  return { events: result, collapsedCount };
}
