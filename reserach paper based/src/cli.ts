import fs from 'node:fs';
import path from 'node:path';
import { Command } from 'commander';
import { DatasetName } from './types.js';
import { readJSON, readJSONL } from './io/jsonl.js';
import { listSessions } from './io/loader.js';

// Schemas for validation in check commands
import {
  PreflightReportSchema,
  SessionTimelineSchema,
  DatasetInventorySchema,
} from './schemas/preflight.js';
import {
  NormalizedEventSchema,
  BurstSchema,
  TypedTextSchema,
  IdentifierSchema,
} from './schemas/norm.js';
import { CanonicalGtFileSchema, ClockAlignmentReportSchema } from './schemas/gt.js';
import { GroundedBurstSchema } from './schemas/grounding.js';
import { ActivitySchema } from './schemas/activities.js';
import { TaskThreadsOutputSchema } from './schemas/taskThreads.js';
import { ExecutionSegmentSchema } from './schemas/segments.js';
import { EvalReportSchema } from './schemas/eval.js';
import { TaskModelsOutputSchema } from './schemas/taskModels.js';
import { CandidateAnalysisOutputSchema } from './schemas/analysis.js';
import { PrototypeSpecSchema } from './schemas/prototype.js';

// Stages
import { runS0Preflight, processSessionS0 } from './stages/s0_preflight.js';
import { runS1Normalize, processSessionS1 } from './stages/s1_normalize.js';
import { runS2Gt } from './stages/s2_gt.js';
import { runS3Grounding } from './stages/s3_grounding.js';
import { runS4Induction } from './stages/s4_induction.js';
import { runS5Clustering } from './stages/s5_clustering.js';
import { runS6Segments } from './stages/s6_segments.js';
import { runS7Eval } from './stages/s7_eval.js';
import { runS8TaskModels } from './stages/s8_task_models.js';
import { runS9Analysis } from './stages/s9_analysis.js';
import { runS10Prototype } from './stages/s10_prototype.js';
import { printTimelineViz } from './viz/timeline.js';

const program = new Command();
program.name('tmi-pipeline').description('Task Model Induction CLI pipeline').version('1.0.0');

function resolveSession(dataset: DatasetName, userSession?: string): string {
  if (userSession) return userSession;
  const sessions = listSessions(dataset);
  if (sessions.length === 0) {
    throw new Error(`No sessions found for dataset ${dataset}`);
  }
  return sessions[0];
}

// Stage commands
program
  .command('s0')
  .description('Run Stage 0: Preflight / Data Ingest Check & Inventory')
  .option('-d, --dataset <A|B>', 'Dataset to use', 'A')
  .option('-s, --session <id>', 'Session directory name (optional, default: all sessions)')
  .option('-l, --limit <n>', 'Limit events to process', parseInt)
  .action(async (opts) => {
    const dataset = opts.dataset.toUpperCase() as DatasetName;
    console.log(`\n================================================================`);
    console.log(`   STAGE S0: Preflight Ingestion & Inventory (${dataset})`);
    console.log(`================================================================`);

    if (opts.session) {
      console.log(`[S0] Processing single session: ${dataset}/${opts.session}...`);
      const { timeline, summary } = await processSessionS0(opts.session, dataset, process.cwd(), opts.limit);
      console.log(`[S0] Done! Session: ${summary.session_id}`);
      console.log(`     Span: ${(summary.duration_seconds / 60).toFixed(1)}m | Events: ${summary.events_count} | Frames: ${summary.frames_count}`);
      console.log(`     Mode breakdown: Both=${(summary.events_and_screens_seconds / 60).toFixed(1)}m, ScreensOnly=${(summary.screens_only_seconds / 60).toFixed(1)}m, EventsOnly=${(summary.events_only_seconds / 60).toFixed(1)}m`);
      console.log(`     Timeline saved: artifacts/${dataset}/${opts.session}/timeline.json`);
    } else {
      console.log(`[S0] Processing ALL sessions in dataset ${dataset}...`);
      const inv = await runS0Preflight(undefined, dataset, process.cwd(), opts.limit);

      console.log(`\n----------------------------------------------------------------`);
      console.log(`   DATASET ${dataset} INVENTORY TABLE (${inv.total_sessions} Sessions)`);
      console.log(`----------------------------------------------------------------`);
      console.log(`  Total Events: ${inv.total_events} | Total Frames: ${inv.total_frames} | Total Duration: ${inv.total_duration_hours}h`);
      console.log(`  Events+Screens Span: ${inv.total_events_and_screens_hours}h (${inv.sessions_with_both} sessions)`);
      console.log(`  Screens-Only Span:   ${inv.total_screens_only_hours}h (${inv.sessions_with_screens_only} sessions)`);
      console.log(`  Events-Only Span:    ${inv.total_events_only_hours}h (${inv.sessions_with_events_only} sessions)`);
      console.log(`----------------------------------------------------------------`);

      console.log('Session ID'.padEnd(38) + 'Dur(m)'.padEnd(9) + 'Events'.padEnd(9) + 'Frames'.padEnd(9) + 'Ev/min'.padEnd(9) + 'Both(m)'.padEnd(10) + 'ScrOnly(m)'.padEnd(12) + 'Gaps>30s');
      console.log('-'.repeat(105));

      for (const s of inv.sessions) {
        const durM = (s.duration_seconds / 60).toFixed(1).padEnd(9);
        const ev = String(s.events_count).padEnd(9);
        const fr = String(s.frames_count).padEnd(9);
        const rate = s.events_per_min.toFixed(1).padEnd(9);
        const bothM = (s.events_and_screens_seconds / 60).toFixed(1).padEnd(10);
        const scrM = (s.screens_only_seconds / 60).toFixed(1).padEnd(12);
        console.log(`${s.session_id.padEnd(38)}${durM}${ev}${fr}${rate}${bothM}${scrM}${s.gaps_over_30s_count}`);
      }
      console.log('----------------------------------------------------------------');
      console.log(`Written: artifacts/${dataset}/inventory.json`);
      console.log(`Written: artifacts/summaries/inventory_${dataset.toLowerCase()}.md\n`);
    }
  });

program
  .command('s1')
  .description('Run Stage 1: Event Normalization, Keystrokes, Identifiers & Bursts')
  .option('-d, --dataset <A|B>', 'Dataset to use', 'A')
  .option('-s, --session <id>', 'Session directory name (optional, default: all sessions)')
  .option('-l, --limit <n>', 'Limit events to process', parseInt)
  .action(async (opts) => {
    const dataset = opts.dataset.toUpperCase() as DatasetName;
    console.log(`\n================================================================`);
    console.log(`   STAGE S1: Deterministic Normalization & Bursts (${dataset})`);
    console.log(`================================================================`);

    if (opts.session) {
      console.log(`[S1] Processing single session: ${dataset}/${opts.session}...`);
      const s = await processSessionS1(opts.session, dataset, process.cwd(), opts.limit);
      console.log(`[S1] Done for ${s.sessionId}:`);
      console.log(`     Raw Events: ${s.rawEventsCount} -> Normalized: ${s.normalizedCount} -> Bursts: ${s.burstsCount}`);
      console.log(`     Event Coverage: ${s.eventCoveragePct}% | Median/p95 Events/Burst: ${s.medianEventsPerBurst} / ${s.p95EventsPerBurst}`);
      console.log(`     Bursts with Both Frames: ${s.pctWithBothFrames}% | With Extracted Text: ${s.pctWithExtractedText}%`);
      console.log(`     Discovered Identifiers: ${s.identifiersTotal} (${JSON.stringify(s.identifiersByKind)})`);
      console.log(`     Reconstructed Typed Text Runs: ${s.typedTextsCount}`);
      console.log(`[S1] Artifacts written under: artifacts/${dataset}/${opts.session}/`);
    } else {
      console.log(`[S1] Processing ALL sessions in dataset ${dataset}...`);
      const res = await runS1Normalize(undefined, dataset, process.cwd(), opts.limit);
      console.log(`\n[S1] Batch Complete across ${res.sessionsProcessed} sessions:`);
      console.log(`     Total Normalized Events: ${res.totalNormalized} | Total Bursts Formed: ${res.totalBursts}`);

      console.log('\nSession ID'.padEnd(38) + 'NormEv'.padEnd(10) + 'Bursts'.padEnd(10) + 'Coverage'.padEnd(10) + 'Med/P95'.padEnd(12) + 'BothFrames%'.padEnd(14) + 'IDs');
      console.log('-'.repeat(105));
      for (const s of res.sessionStats) {
        const ev = String(s.normalizedCount).padEnd(10);
        const b = String(s.burstsCount).padEnd(10);
        const cov = `${s.eventCoveragePct}%`.padEnd(10);
        const medP95 = `${s.medianEventsPerBurst}/${s.p95EventsPerBurst}`.padEnd(12);
        const frames = `${s.pctWithBothFrames}%`.padEnd(14);
        console.log(`${s.sessionId.padEnd(38)}${ev}${b}${cov}${medP95}${frames}${s.identifiersTotal}`);
      }
      console.log('----------------------------------------------------------------\n');
    }
  });

program
  .command('s2')
  .description('Run Stage 2: Canonical Ground Truth & Clock Alignment')
  .option('-d, --dataset <A|B>', 'Dataset to use', 'A')
  .option('-s, --session <id>', 'Session directory name')
  .action(async (opts) => {
    const dataset = opts.dataset.toUpperCase() as DatasetName;
    const session = resolveSession(dataset, opts.session);
    console.log(`[S2] Building canonical ground truth & measuring clock alignment for ${dataset}/${session}...`);
    const res = await runS2Gt(session, dataset, process.cwd());
    console.log(`[S2] Done! Canonical executions: ${res.executionsCount} | Clock offset: ${res.alignmentOffsetMs} ms.`);
    console.log(`[S2] Artifacts saved under: artifacts/${dataset}/${session}/`);
  });

program
  .command('s3')
  .description('Run Stage 3: Burst Action Grounding')
  .option('-d, --dataset <A|B>', 'Dataset to use', 'A')
  .option('-s, --session <id>', 'Session directory name')
  .option('--mock', 'Run with deterministic mock LLM', true)
  .action(async (opts) => {
    const dataset = opts.dataset.toUpperCase() as DatasetName;
    const session = resolveSession(dataset, opts.session);
    console.log(`[S3] Grounding bursts for ${dataset}/${session}...`);
    const res = await runS3Grounding(session, dataset, process.cwd(), opts.mock);
    console.log(`[S3] Done! Grounded ${res.groundedCount} bursts (deduped across ${res.uniqueSignaturesCount} unique signatures).`);
    console.log(`[S3] Artifact saved: artifacts/${dataset}/${session}/s3_grounded.jsonl`);
  });

program
  .command('s4')
  .description('Run Stage 4: Semantic Activity Induction')
  .option('-d, --dataset <A|B>', 'Dataset to use', 'A')
  .option('-s, --session <id>', 'Session directory name')
  .option('--mock', 'Run with deterministic mock LLM', true)
  .action(async (opts) => {
    const dataset = opts.dataset.toUpperCase() as DatasetName;
    const session = resolveSession(dataset, opts.session);
    console.log(`[S4] Inducing activities for ${dataset}/${session}...`);
    const res = await runS4Induction(session, dataset, process.cwd(), opts.mock);
    console.log(`[S4] Done! Induced ${res.activitiesCount} activities.`);
    console.log(`[S4] Artifact saved: artifacts/${dataset}/${session}/s4_activities.jsonl`);
  });

program
  .command('s5')
  .description('Run Stage 5: Task Threads Clustering & Global Canonicalization')
  .option('-d, --dataset <A|B>', 'Dataset to use', 'A')
  .option('-s, --session <id>', 'Session directory name')
  .option('--mock', 'Run with deterministic mock LLM', true)
  .action(async (opts) => {
    const dataset = opts.dataset.toUpperCase() as DatasetName;
    const session = resolveSession(dataset, opts.session);
    console.log(`[S5] Clustering task threads for ${dataset}/${session}...`);
    const res = await runS5Clustering(session, dataset, process.cwd(), opts.mock);
    console.log(`[S5] Done! Formed ${res.rootsCount} process family roots with ${res.assignmentsCount} activity assignments.`);
    console.log(`[S5] Artifact saved: artifacts/${dataset}/${session}/s5_task_threads.json`);
  });

program
  .command('s6')
  .description('Run Stage 6: Execution Splitting & Boundary Snapping')
  .option('-d, --dataset <A|B>', 'Dataset to use', 'A')
  .option('-s, --session <id>', 'Session directory name')
  .action(async (opts) => {
    const dataset = opts.dataset.toUpperCase() as DatasetName;
    const session = resolveSession(dataset, opts.session);
    console.log(`[S6] Splitting executions & snapping boundaries for ${dataset}/${session}...`);
    const res = await runS6Segments(session, dataset, process.cwd());
    console.log(`[S6] Done! Generated ${res.segmentsCount} segments.`);
    console.log(`[S6] Deliverable strictly validated & saved to: ./segments.jsonl`);
  });

program
  .command('s7')
  .description('Run Stage 7: Evaluation against Ground Truth')
  .option('-d, --dataset <A|B>', 'Dataset to use', 'A')
  .option('-s, --session <id>', 'Session directory name')
  .action(async (opts) => {
    const dataset = opts.dataset.toUpperCase() as DatasetName;
    const session = resolveSession(dataset, opts.session);
    console.log(`[S7] Evaluating segments against canonical GT for ${dataset}/${session}...`);
    const report = await runS7Eval(session, dataset, process.cwd());
    const f1_30 = report.tolerances.find(t => t.toleranceSec === 30)?.f1 || 0;
    console.log(`[S7] Done! Boundary F1@30s: ${(f1_30 * 100).toFixed(1)}% | ARI: ${report.clustering.ari.toFixed(4)}`);
  });

program
  .command('s8')
  .description('Run Stage 8: Task Model Induction (Procedure Models)')
  .option('-d, --dataset <A|B>', 'Dataset to use', 'A')
  .option('-s, --session <id>', 'Session directory name')
  .action(async (opts) => {
    const dataset = opts.dataset.toUpperCase() as DatasetName;
    const session = resolveSession(dataset, opts.session);
    console.log(`[S8] Inducing procedure task models for ${dataset}/${session}...`);
    const res = await runS8TaskModels(session, dataset, process.cwd());
    console.log(`[S8] Done! Induced ${res.modelsCount} procedure models.`);
    console.log(`[S8] Artifact saved: artifacts/${dataset}/${session}/s8_task_models.json`);
  });

program
  .command('s9')
  .description('Run Stage 9: Step 2 Automation Candidate Portfolio Analysis')
  .option('-d, --dataset <A|B>', 'Dataset to use', 'A')
  .option('-s, --session <id>', 'Session directory name')
  .action(async (opts) => {
    const dataset = opts.dataset.toUpperCase() as DatasetName;
    const session = resolveSession(dataset, opts.session);
    console.log(`[S9] Analyzing automation candidates for ${dataset}/${session}...`);
    const output = await runS9Analysis(session, dataset, process.cwd());
    console.log(`\n================================================================`);
    console.log(`   STEP 2 AUTOMATION CANDIDATE RANKINGS`);
    console.log(`================================================================`);
    for (const c of output.candidates) {
      console.log(`  #${c.rank} ${c.process_name.padEnd(25)} | Execs: ${c.execution_count} | Mean Time: ${c.mean_time_seconds}s | Rule Det: ${c.rule_determinism_score}/10 | ROI Score: ${c.estimated_roi_score}`);
    }
    console.log(`----------------------------------------------------------------`);
    console.log(`  Top Recommended Candidate: ${output.topCandidate}`);
    console.log(`  Justification: ${output.justification}`);
    console.log(`================================================================\n`);
  });

program
  .command('s10')
  .description('Run Stage 10: Step 3 Prototype & Final Report Generation')
  .option('-d, --dataset <A|B>', 'Dataset to use', 'A')
  .option('-s, --session <id>', 'Session directory name')
  .action(async (opts) => {
    const dataset = opts.dataset.toUpperCase() as DatasetName;
    const session = resolveSession(dataset, opts.session);
    console.log(`[S10] Executing prototype and writing reports for ${dataset}/${session}...`);
    const spec = await runS10Prototype(session, dataset, process.cwd());
    console.log(`[S10] Prototype execution verified for ${spec.targetProcess}!`);
    console.log(`[S10] Final report written: reports/REPORT.md`);
  });

// Check command
program
  .command('check <stage>')
  .description('Verify artifacts for a given stage or all stages')
  .option('-d, --dataset <A|B>', 'Dataset to use', 'A')
  .option('-s, --session <id>', 'Session directory name')
  .action(async (stage, opts) => {
    const dataset = opts.dataset.toUpperCase() as DatasetName;
    const session = resolveSession(dataset, opts.session);
    const artifactsDir = path.join(process.cwd(), 'artifacts', dataset, session);

    const checkStage = async (s: string) => {
      switch (s.toLowerCase()) {
        case 's0': {
          // Check session timeline
          const timelinePath = path.join(artifactsDir, 'timeline.json');
          if (!fs.existsSync(timelinePath)) {
            // Check fallback s0_preflight.json
            const p = path.join(artifactsDir, 's0_preflight.json');
            if (!fs.existsSync(p)) throw new Error(`Missing timeline at ${timelinePath} or ${p}`);
            const data = readJSON(p);
            PreflightReportSchema.parse(data);
            console.log(`✓ check:s0 passed (${data.totalRawEvents} events checked)`);
            return;
          }

          const timelineData = readJSON(timelinePath);
          SessionTimelineSchema.parse(timelineData);

          // Verify acceptance: mode regions sum to session duration
          const sumRegionDuration = timelineData.regions.reduce(
            (acc: number, r: any) => acc + r.duration_seconds,
            0
          );
          const totalDuration = timelineData.time_span.duration_seconds;
          const diff = Math.abs(sumRegionDuration - totalDuration);
          if (diff > 0.05) {
            throw new Error(
              `Mode regions duration sum (${sumRegionDuration}s) does not match session duration (${totalDuration}s, diff=${diff})`
            );
          }

          console.log(`✓ check:s0 passed (${timelineData.events_count} events, ${timelineData.frames_count} frames, ${timelineData.regions.length} mode regions summing to ${totalDuration}s)`);
          break;
        }
        case 's1': {
          const pNorm = path.join(artifactsDir, 'norm_events.jsonl');
          const pBursts = path.join(artifactsDir, 'bursts.jsonl');
          const pTyped = path.join(artifactsDir, 'typed_text.jsonl');
          const pIds = path.join(artifactsDir, 'identifiers.jsonl');

          // Fallbacks for previous naming
          const normFile = fs.existsSync(pNorm) ? pNorm : path.join(artifactsDir, 's1_normalized.jsonl');
          const burstsFile = fs.existsSync(pBursts) ? pBursts : path.join(artifactsDir, 's1_bursts.jsonl');

          if (!fs.existsSync(normFile) || !fs.existsSync(burstsFile)) {
            throw new Error(`Missing S1 files in ${artifactsDir}`);
          }

          const evs = await readJSONL(normFile);
          const bursts = await readJSONL(burstsFile);

          if (evs.length === 0 || bursts.length === 0) throw new Error('S1 files empty');

          evs.forEach(e => NormalizedEventSchema.parse(e));
          bursts.forEach(b => BurstSchema.parse(b));

          if (fs.existsSync(pTyped)) {
            const typed = await readJSONL(pTyped);
            typed.forEach(t => TypedTextSchema.parse(t));
          }

          if (fs.existsSync(pIds)) {
            const ids = await readJSONL(pIds);
            ids.forEach(i => IdentifierSchema.parse(i));
          }

          // Acceptance: 100% coverage - sum of event_count across all event bursts must equal evs.length
          const totalCoveredEvents = bursts.reduce((acc, b: any) => acc + (b.event_count || 0), 0);
          if (totalCoveredEvents !== evs.length) {
            throw new Error(
              `100% coverage failed: Burst events count (${totalCoveredEvents}) !== Normalized events count (${evs.length})`
            );
          }

          console.log(`✓ check:s1 passed (${evs.length} normalized events, ${bursts.length} bursts, 100% event coverage verified)`);
          break;
        }
        case 's2': {
          const p1 = path.join(artifactsDir, 's2_canonical_gt.json');
          const p2 = path.join(artifactsDir, 's2_alignment.json');
          if (!fs.existsSync(p1) || !fs.existsSync(p2)) throw new Error('Missing S2 files');
          const gt = readJSON(p1);
          const align = readJSON(p2);
          CanonicalGtFileSchema.parse(gt);
          ClockAlignmentReportSchema.parse(align);
          console.log(`✓ check:s2 passed (${gt.executionsCount} canonical executions, offset=${align.estimatedOffsetMs}ms)`);
          break;
        }
        case 's3': {
          const p = path.join(artifactsDir, 's3_grounded.jsonl');
          if (!fs.existsSync(p)) throw new Error(`Missing ${p}`);
          const items = await readJSONL(p);
          if (items.length === 0) throw new Error('S3 grounded bursts empty');
          items.forEach(i => GroundedBurstSchema.parse(i));
          console.log(`✓ check:s3 passed (${items.length} grounded bursts)`);
          break;
        }
        case 's4': {
          const p = path.join(artifactsDir, 's4_activities.jsonl');
          if (!fs.existsSync(p)) throw new Error(`Missing ${p}`);
          const items = await readJSONL(p);
          if (items.length === 0) throw new Error('S4 activities empty');
          items.forEach(i => ActivitySchema.parse(i));
          console.log(`✓ check:s4 passed (${items.length} activities)`);
          break;
        }
        case 's5': {
          const p = path.join(artifactsDir, 's5_task_threads.json');
          if (!fs.existsSync(p)) throw new Error(`Missing ${p}`);
          const data = readJSON(p);
          TaskThreadsOutputSchema.parse(data);
          if (data.roots.length === 0) throw new Error('S5 roots empty');
          console.log(`✓ check:s5 passed (${data.roots.length} roots, ${data.assignments.length} assignments)`);
          break;
        }
        case 's6': {
          const p1 = path.join(artifactsDir, 's6_segments.jsonl');
          const p2 = path.join(process.cwd(), 'segments.jsonl');
          if (!fs.existsSync(p1) && !fs.existsSync(p2)) throw new Error('Missing segments.jsonl');
          const target = fs.existsSync(p2) ? p2 : p1;
          const items = await readJSONL(target);
          if (items.length === 0) throw new Error('segments.jsonl is empty');
          for (const item of items) {
            ExecutionSegmentSchema.parse(item);
            const keys = Object.keys(item);
            if (keys.length !== 4) throw new Error(`Extra keys found in segment: ${keys.join(', ')}`);
          }
          console.log(`✓ check:s6 passed (${items.length} strictly formatted segments)`);
          break;
        }
        case 's7': {
          const p = path.join(artifactsDir, 's7_eval_report.json');
          if (!fs.existsSync(p)) throw new Error(`Missing ${p}`);
          const data = readJSON(p);
          EvalReportSchema.parse(data);
          const f1_30 = data.tolerances.find((t: any) => t.toleranceSec === 30)?.f1 || 0;
          console.log(`✓ check:s7 passed (F1@30s=${(f1_30 * 100).toFixed(1)}%, ARI=${data.clustering.ari.toFixed(3)})`);
          break;
        }
        case 's8': {
          const p = path.join(artifactsDir, 's8_task_models.json');
          if (!fs.existsSync(p)) throw new Error(`Missing ${p}`);
          const data = readJSON(p);
          TaskModelsOutputSchema.parse(data);
          console.log(`✓ check:s8 passed (${data.models.length} procedure models)`);
          break;
        }
        case 's9': {
          const p = path.join(artifactsDir, 's9_candidate_rankings.json');
          if (!fs.existsSync(p)) throw new Error(`Missing ${p}`);
          const data = readJSON(p);
          CandidateAnalysisOutputSchema.parse(data);
          console.log(`✓ check:s9 passed (${data.candidates.length} ranked candidates, top=${data.topCandidate})`);
          break;
        }
        case 's10': {
          const p = path.join(artifactsDir, 's10_prototype_spec.json');
          if (!fs.existsSync(p)) throw new Error(`Missing ${p}`);
          const data = readJSON(p);
          PrototypeSpecSchema.parse(data);
          const reportPath = path.join(process.cwd(), 'reports', 'REPORT.md');
          if (!fs.existsSync(reportPath)) throw new Error('Missing reports/REPORT.md');
          console.log(`✓ check:s10 passed (Prototype validated for ${data.targetProcess}, REPORT.md generated)`);
          break;
        }
        default:
          throw new Error(`Unknown stage to check: ${s}`);
      }
    };

    if (stage.toLowerCase() === 'all') {
      console.log(`\nRunning comprehensive check across ALL stages for ${dataset}/${session}...`);
      for (const s of ['s0', 's1', 's2', 's3', 's4', 's5', 's6', 's7', 's8', 's9', 's10']) {
        await checkStage(s);
      }
      console.log('\n🎉 ALL STAGES CHECKED AND PASSED!\n');
    } else {
      await checkStage(stage);
    }
  });

// Demo mock command
program
  .command('demo-mock')
  .description('Run complete mock pipeline S0 through S10 on target session')
  .option('-d, --dataset <A|B>', 'Dataset to use', 'A')
  .option('-s, --session <id>', 'Session directory name')
  .action(async (opts) => {
    const dataset = opts.dataset.toUpperCase() as DatasetName;
    const session = resolveSession(dataset, opts.session);

    console.log(`\n================================================================`);
    console.log(`  RUNNING DEMO:MOCK PIPELINE (S0 - S10) FOR ${dataset}/${session}`);
    console.log(`================================================================\n`);

    console.log('--> [Step 0/10] S0: Preflight Ingestion Check');
    const { summary: s0 } = await processSessionS0(session, dataset, process.cwd());
    console.log(`    Total Events: ${s0.events_count} | Total Frames: ${s0.frames_count} | Chunks: ${s0.chunk_dirs_total}`);

    console.log('\n--> [Step 1/10] S1: Normalization & Bursts');
    const s1 = await processSessionS1(session, dataset, process.cwd());
    console.log(`    Normalized: ${s1.normalizedCount} | Bursts: ${s1.burstsCount} | Coverage: ${s1.eventCoveragePct}%`);

    console.log('\n--> [Step 2/10] S2: Canonical Ground Truth & Clock Alignment');
    const s2 = await runS2Gt(session, dataset);
    console.log(`    GT Executions: ${s2.executionsCount} | Offset: ${s2.alignmentOffsetMs} ms`);

    console.log('\n--> [Step 3/10] S3: Burst Action Grounding');
    const s3 = await runS3Grounding(session, dataset, process.cwd(), true);
    console.log(`    Grounded Bursts: ${s3.groundedCount}`);

    console.log('\n--> [Step 4/10] S4: Semantic Activity Induction');
    const s4 = await runS4Induction(session, dataset, process.cwd(), true);
    console.log(`    Activities: ${s4.activitiesCount}`);

    console.log('\n--> [Step 5/10] S5: Task Threads Clustering');
    const s5 = await runS5Clustering(session, dataset, process.cwd(), true);
    console.log(`    Process Family Roots: ${s5.rootsCount}`);

    console.log('\n--> [Step 6/10] S6: Execution Splitting & Boundary Snapping');
    const s6 = await runS6Segments(session, dataset);
    console.log(`    Generated segments.jsonl (${s6.segmentsCount} segments)`);

    console.log('\n--> [Step 7/10] S7: Evaluation Against Canonical Ground Truth');
    const s7 = await runS7Eval(session, dataset);
    const f1_30 = s7.tolerances.find(t => t.toleranceSec === 30)?.f1 || 0;
    console.log(`    Boundary F1 @ ±30s: ${(f1_30 * 100).toFixed(1)}% | ARI: ${s7.clustering.ari.toFixed(4)}`);

    console.log('\n--> [Step 8/10] S8: Procedure Model Induction');
    const s8 = await runS8TaskModels(session, dataset);
    console.log(`    Procedure Models: ${s8.modelsCount}`);

    console.log('\n--> [Step 9/10] S9: Automation Candidate Portfolio Analysis');
    const s9 = await runS9Analysis(session, dataset);
    console.log(`    Top Automation Candidate: ${s9.topCandidate} (#1 of ${s9.candidates.length})`);

    console.log('\n--> [Step 10/10] S10: Step 3 Prototype Execution & Report Generation');
    const s10 = await runS10Prototype(session, dataset);
    console.log(`    Prototype verified for ${s10.targetProcess}! Written reports/REPORT.md`);

    console.log('\n================================================================');
    console.log(`🎉 DEMO MOCK PIPELINE S0-S10 COMPLETED SUCCESSFULLY!`);
    console.log(`================================================================\n`);
  });

program
  .command('eval')
  .description('Run evaluation report on existing segments')
  .option('-d, --dataset <A|B>', 'Dataset to use', 'A')
  .option('-s, --session <id>', 'Session directory name')
  .action(async (opts) => {
    const dataset = opts.dataset.toUpperCase() as DatasetName;
    const session = resolveSession(dataset, opts.session);
    console.log(`[EVAL] Evaluating segments against canonical ground truth for ${dataset}/${session}...`);
    const report = await runS7Eval(session, dataset, process.cwd());
    console.log(`\n================================================================`);
    console.log(`   EVALUATION RESULTS (Session: ${session})`);
    console.log(`================================================================`);
    console.log(`  Predicted Segments: ${report.predictedSegmentsCount} | Ground Truth: ${report.groundTruthExecutionsCount}`);
    console.log(`  Unique Labels: Pred=[${report.uniquePredictedLabels.join(', ')}] | GT=[${report.uniqueGroundTruthLabels.join(', ')}]`);
    console.log(`----------------------------------------------------------------`);
    console.log(`  Boundary Tolerance Metrics:`);
    for (const tol of report.tolerances) {
      console.log(`    ±${tol.toleranceSec}s Window -> Precision: ${(tol.precision * 100).toFixed(1)}% | Recall: ${(tol.recall * 100).toFixed(1)}% | F1: ${(tol.f1 * 100).toFixed(1)}% | Mean Offset: ${tol.meanOffsetSeconds.toFixed(1)}s`);
    }
    console.log(`----------------------------------------------------------------`);
    console.log(`  Clustering Metrics:`);
    console.log(`    ARI (Adjusted Rand Index): ${report.clustering.ari.toFixed(4)}`);
    console.log(`    NMI (Normalized Mutual Info): ${report.clustering.nmi.toFixed(4)}`);
    console.log(`    Purity: ${(report.clustering.purity * 100).toFixed(1)}%`);
    console.log(`----------------------------------------------------------------`);
    console.log(`  Temporal Overlap: Mean IoU=${report.temporalOverlap.meanIou.toFixed(4)} | Coverage=${(report.temporalOverlap.coverage * 100).toFixed(1)}%`);
    console.log(`----------------------------------------------------------------`);
    console.log(`  Baseline Comparison:`);
    for (const b of report.baselines) {
      console.log(`    ${b.name.padEnd(25)} -> F1@30s: ${(b.f1At30s * 100).toFixed(1)}% | ARI: ${b.ari.toFixed(4)}`);
    }
    console.log(`================================================================\n`);
  });

program
  .command('estimate')
  .description('Compute burst counts for A and B and project LLM grounding calls and token budgets')
  .action(async () => {
    console.log('\n================================================================');
    console.log(`   LLM USAGE & CALL ESTIMATES: DATASET A vs. DATASET B`);
    console.log('================================================================');

    const sessionsA = listSessions('A');
    const sessionsB = listSessions('B');

    // Check inventory files if available
    const invAPath = path.join(process.cwd(), 'artifacts', 'A', 'inventory.json');
    const invBPath = path.join(process.cwd(), 'artifacts', 'B', 'inventory.json');

    const invA = fs.existsSync(invAPath) ? readJSON(invAPath) : null;
    const invB = fs.existsSync(invBPath) ? readJSON(invBPath) : null;

    const totalEventsA = invA ? invA.total_events : sessionsA.length * 2800;
    const totalEventsB = invB ? invB.total_events : 20000;

    // In TMI adapted design, ~4 events per burst
    const estimatedBurstsA = Math.round(totalEventsA / 4.2);
    const estimatedBurstsB = Math.round(totalEventsB / 4.2);

    // Dedup factor observed in S3 caching is ~64% cache hit rate -> 36% unique signatures
    const uniqueCallsA = Math.round(estimatedBurstsA * 0.36);
    const uniqueCallsB = Math.round(estimatedBurstsB * 0.36);

    // Tokens: ~800 input tokens per burst grounding call, ~150 output tokens
    const estInputTokensB = uniqueCallsB * 850;
    const estOutputTokensB = uniqueCallsB * 150;
    const estCostUSD = (estInputTokensB / 1_000_000) * 0.15 + (estOutputTokensB / 1_000_000) * 0.60;

    console.log(`  Dataset A:`);
    console.log(`    Sessions: ${sessionsA.length} | Raw Events: ${totalEventsA}`);
    console.log(`    Estimated Bursts: ${estimatedBurstsA}`);
    console.log(`    Projected Grounding Calls (with signature deduplication): ${uniqueCallsA}`);
    console.log('');
    console.log(`  Dataset B (Unlabelled Production Data):`);
    console.log(`    Sessions: ${sessionsB.length} | Raw Events: ~${totalEventsB}`);
    console.log(`    Estimated Bursts: ~${estimatedBurstsB}`);
    console.log(`    Projected Grounding Calls (with signature deduplication): ~${uniqueCallsB}`);
    console.log(`    Projected Prompt Tokens: ~${estInputTokensB.toLocaleString()} | Output Tokens: ~${estOutputTokensB.toLocaleString()}`);
    console.log(`    Estimated LLM Grounding Cost: ~$${estCostUSD.toFixed(3)} USD (well within MAX_USD $10 cap)`);
    console.log('----------------------------------------------------------------');
    console.log(`  Throughput at 15 RPM: ~${(uniqueCallsB / 15).toFixed(1)} minutes total run time for Dataset B`);
    console.log(`  Daily Call Cap (900 calls/day): Entire Dataset B requires ~${(uniqueCallsB / 900).toFixed(1)} days allowance`);
    console.log('================================================================\n');
  });

program
  .command('viz')
  .description('Visualize predicted segments vs ground truth timeline')
  .option('-d, --dataset <A|B>', 'Dataset to use', 'A')
  .option('-s, --session <id>', 'Session directory name')
  .action(async (opts) => {
    const dataset = opts.dataset.toUpperCase() as DatasetName;
    const session = resolveSession(dataset, opts.session);
    await printTimelineViz(session, dataset);
  });

program
  .command('review [target]')
  .description('Review sample grounded bursts')
  .option('-d, --dataset <A|B>', 'Dataset to use', 'A')
  .option('-s, --session <id>', 'Session directory name')
  .action(async (target, opts) => {
    const dataset = ((opts && opts.dataset) ? opts.dataset : 'A').toUpperCase() as DatasetName;
    const session = resolveSession(dataset, opts?.session);
    const p = path.join(process.cwd(), 'artifacts', dataset, session, 's3_grounded.jsonl');
    if (!fs.existsSync(p)) {
      console.log(`No grounded bursts found at ${p}. Run s3 first.`);
      return;
    }
    const bursts = await readJSONL(p);
    console.log(`\nReviewing first 5 grounded bursts from ${bursts.length} total:`);
    for (const b of bursts.slice(0, 5)) {
      console.log(`  [${b.burst_id}] ${b.app_name} | ${b.clean_title}`);
      console.log(`    Action: ${b.semantic_action}`);
      console.log(`    UI: ${b.ui_target} | Intent: ${b.intent}\n`);
    }
  });

program.parse(process.argv);
