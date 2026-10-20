import fs from 'node:fs';
import { SessionInfo } from '../io/loader.js';
import { readJSONL, readJSON } from '../io/jsonl.js';
import { CanonicalExecution, CanonicalGtFile } from '../schemas/gt.js';

export async function buildCanonicalGt(sessionInfo: SessionInfo): Promise<CanonicalGtFile> {
  const rawExecutions: any[] = [];
  const families = new Set<string>();
  let runId = '';
  let operator = '';
  let department = '';
  let sessionEndIso = '';

  // First priority: gt_manifest.json
  if (sessionInfo.hasGtManifest && sessionInfo.gtManifestPath) {
    try {
      const manifest = readJSON(sessionInfo.gtManifestPath);
      runId = manifest.run_id || '';
      operator = manifest.session?.operator || '';
      department = manifest.session?.operator_dept || '';
      sessionEndIso = manifest.session?.end_ts || '';

      if (Array.isArray(manifest.processes)) {
        for (const proc of manifest.processes) {
          const code = proc.code || '';
          const familyName = proc.family_name || code;
          families.add(code);

          if (Array.isArray(proc.executions)) {
            for (const exec of proc.executions) {
              const startMs = Date.parse(exec.start_ts);
              const endMs = exec.end_ts ? Date.parse(exec.end_ts) : NaN;
              rawExecutions.push({
                exec_id: exec.exec_id || `gt_${code}_${exec.case_id || ''}_${startMs}`,
                code,
                family_name: familyName,
                variant: exec.variant || null,
                case_id: exec.case_id || '',
                start_iso: exec.start_ts,
                end_iso: exec.end_ts,
                start_ms: startMs,
                end_ms: endMs,
                apps: Array.isArray(exec.apps) ? exec.apps : [],
                continues_from_prev: exec.continues_from_prev,
                continues_to_next: exec.continues_to_next,
                split_id: exec.split_id || null,
                phase: exec.phase,
                seq: exec.seq,
              });
            }
          }
        }
      }
    } catch (err) {
      // Fall back to gt.jsonl
    }
  }

  // Fallback or validation via gt.jsonl if manifest had no executions
  if (rawExecutions.length === 0 && sessionInfo.hasGt && sessionInfo.gtPath) {
    const rawGtEvents = await readJSONL<any>(sessionInfo.gtPath);
    let currentProc: any = null;
    let procStartMs = 0;
    let procStartIso = '';

    for (let i = 0; i < rawGtEvents.length; i++) {
      const line = rawGtEvents[i];
      if (line.event === 'run_config') {
        runId = line.run_id || runId;
        operator = line.operator || operator;
        department = line.operator_dept || department;
      } else if (line.event === 'process_started') {
        if (currentProc) {
          const endMs = Date.parse(line.ts_utc);
          rawExecutions.push({
            exec_id: `gt_${currentProc.process_code}_${currentProc.case_id || ''}_${procStartMs}`,
            code: currentProc.process_code,
            family_name: currentProc.process_name || currentProc.process_code,
            variant: currentProc.process_variant || null,
            case_id: currentProc.case_id || '',
            start_iso: procStartIso,
            end_iso: line.ts_utc,
            start_ms: procStartMs,
            end_ms: endMs,
            apps: [],
          });
          families.add(currentProc.process_code);
        }

        currentProc = line;
        procStartIso = line.ts_utc;
        procStartMs = Date.parse(line.ts_utc);
      } else if (line.event === 'process_switched_out' || line.event === 'process_suspended' || line.event === 'session_ended') {
        if (currentProc) {
          const endMs = Date.parse(line.ts_utc);
          rawExecutions.push({
            exec_id: `gt_${currentProc.process_code}_${currentProc.case_id || ''}_${procStartMs}`,
            code: currentProc.process_code,
            family_name: currentProc.process_name || currentProc.process_code,
            variant: currentProc.process_variant || null,
            case_id: currentProc.case_id || '',
            start_iso: procStartIso,
            end_iso: line.ts_utc,
            start_ms: procStartMs,
            end_ms: endMs,
            apps: [],
          });
          families.add(currentProc.process_code);
          currentProc = null;
        }
      }
    }
  }

  // Sort executions strictly chronologically by start_ms
  rawExecutions.sort((a, b) => a.start_ms - b.start_ms);

  // Defensively resolve null/missing end timestamps
  const canonicalExecutions: CanonicalExecution[] = [];

  for (let i = 0; i < rawExecutions.length; i++) {
    const exec = rawExecutions[i];
    let endIso = exec.end_iso;
    let endMs = exec.end_ms;

    if (!endIso || isNaN(endMs)) {
      // If consecutive execution exists, its start_ts is this execution's end_ts
      if (i + 1 < rawExecutions.length) {
        endIso = rawExecutions[i + 1].start_iso;
        endMs = rawExecutions[i + 1].start_ms;
      } else if (sessionEndIso) {
        endIso = sessionEndIso;
        endMs = Date.parse(sessionEndIso);
      } else {
        // Fallback: estimate 45s duration
        endMs = exec.start_ms + 45000;
        endIso = new Date(endMs).toISOString();
      }
    }

    canonicalExecutions.push({
      ...exec,
      end_iso: endIso,
      end_ms: endMs,
    });
  }

  return {
    sessionId: sessionInfo.sessionId,
    runId,
    operator,
    department,
    executionsCount: canonicalExecutions.length,
    familiesCount: families.size,
    executions: canonicalExecutions,
  };
}
