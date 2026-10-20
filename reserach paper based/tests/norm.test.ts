import { describe, it, expect } from 'vitest';
import { cleanWindowTitle, templateWindowTitle, collapseAppSwitches } from '../src/norm/titles.js';
import { extractIdentifiers, redactText, extractGenericIdentifiers, discoverIdFormats } from '../src/norm/ids.js';
import { reconstructKeystrokes } from '../src/norm/keystrokes.js';
import { formBursts } from '../src/norm/bursts.js';
import { SegmentLineSchema } from '../src/schemas/segments.js';
import { DatasetConfig } from '../src/config.js';
import { NormalizedEvent } from '../src/types.js';

describe('Normalization & Text Processing', () => {
  it('cleans window titles and generates stable templates', () => {
    expect(cleanWindowTitle('財務会計システム - Google Chrome')).toBe('財務会計システム');
    expect(cleanWindowTitle('*m1_reference - Excel')).toBe('m1_reference');
    expect(cleanWindowTitle('Untitled - Notepad')).toBe('Untitled');

    // Title templating
    const titleWithDateAndId = 'Order Processing ORD-182807-001 (2026-07-01 18:32:00)';
    const templated = templateWindowTitle(titleWithDateAndId);
    expect(templated).toContain('<ID>');
    expect(templated).toContain('<DATE>');
    expect(templated).toContain('<TIME>');
  });

  it('discovers ORD-... and INV-... style IDs generically without hardcoded patterns', () => {
    const rawSources = [
      {
        text: 'Reviewing order ORD-182807-001 for customer',
        source: 'extracted_text',
        timestamp_ms: 1000,
      },
      {
        text: 'Completed invoice INV-110635-001',
        source: 'window_title',
        timestamp_ms: 2000,
      },
      {
        text: 'Customer entity: 株式会社エヌ・ティ・ティ・データ 様',
        source: 'extracted_text',
        timestamp_ms: 3000,
      },
      {
        text: 'Document voucher: 987654321',
        source: 'extracted_text',
        timestamp_ms: 4000,
      },
    ];

    const identifiers = extractGenericIdentifiers(rawSources);
    const discoveredValues = identifiers.map(i => i.value);

    // Case IDs discovered
    expect(discoveredValues).toContain('ORD-182807-001');
    expect(discoveredValues).toContain('INV-110635-001');

    // Japanese entity discovered
    const compEntity = identifiers.find(i => i.kind === 'entity');
    expect(compEntity).toBeDefined();

    // Document number discovered
    const docNo = identifiers.find(i => i.value === '987654321');
    expect(docNo?.kind).toBe('doc_no');

    // Dynamic format deduction
    const formats = discoverIdFormats(identifiers);
    expect(formats.length).toBeGreaterThan(0);
    expect(formats.some(f => f.examples.includes('ORD-182807-001'))).toBe(true);
  });

  it('reconstructs typed text honouring backspace, enter, tab, and detects IME', () => {
    const fakeEvents: any[] = [
      { event_type: 'keystroke', timestamp_ms: 1000, payload: { key: 'Key.h' } },
      { event_type: 'keystroke', timestamp_ms: 1100, payload: { key: 'Key.i' } },
      { event_type: 'keystroke', timestamp_ms: 1200, payload: { key: 'Space' } },
      { event_type: 'keystroke', timestamp_ms: 1300, payload: { key: 'Key.x' } },
      { event_type: 'keystroke', timestamp_ms: 1400, payload: { key: 'Backspace' } },
      { event_type: 'keystroke', timestamp_ms: 1500, payload: { key: 'Key.y' } },
      { event_type: 'keystroke', timestamp_ms: 1600, payload: { key: 'Tab' } },
      { event_type: 'keystroke', timestamp_ms: 1700, payload: { key: 'Enter' } },
      // IME trigger key
      { event_type: 'keystroke', timestamp_ms: 1800, payload: { key: 'henkan' } },
    ];

    const typedRuns = reconstructKeystrokes(fakeEvents, 1000);
    expect(typedRuns.length).toBe(1);
    expect(typedRuns[0].text).toBe('hi y\t\n');
    expect(typedRuns[0].ime_suspected).toBe(true);
  });

  it('collapses transient app-switch ping-pongs within collapseWindowMs', () => {
    const rawEvents = [
      { event_type: 'app_switch', app_name: 'chrome', timestamp_ms: 1000 },
      { event_type: 'mouse_click', app_name: 'chrome', timestamp_ms: 1100 },
      // Transient flick to notepad for 400ms then back to chrome
      { event_type: 'app_switch', app_name: 'notepad', timestamp_ms: 2000 },
      { event_type: 'app_switch', app_name: 'chrome', timestamp_ms: 2400 },
      { event_type: 'mouse_click', app_name: 'chrome', timestamp_ms: 3000 },
    ];

    const { events, collapsedCount } = collapseAppSwitches(rawEvents, 1500);
    expect(collapsedCount).toBe(1);
    // Transient app switches were collapsed
    const appSwitches = events.filter(e => e.event_type === 'app_switch');
    expect(appSwitches.length).toBe(1);
  });

  it('guarantees 100% burst coverage over non-dropped events', () => {
    const mockConfig: DatasetConfig = {
      dataset: 'A',
      recorder_process: 'procmine-desktop-agent.exe',
      recorder_process_patterns: ['procmine'],
      idle_gap_threshold_ms: 4000,
      burst_idle_s: 3.0,
      keystroke_idle_threshold_ms: 1500,
      app_switch_collapse_ms: 1500,
      burst_max_events: 10,
      boundary_snap_tolerance_sec: 30,
      eval_tolerance_sec: [15, 30, 60],
      case_id_patterns: [],
      domain_whitelist: [],
    };

    const mockEvents: NormalizedEvent[] = [];
    for (let i = 0; i < 45; i++) {
      mockEvents.push({
        event_id: `ev_${i}`,
        session_id: 'ses_test',
        chunk_id: 'chunk_1',
        timestamp_ms: 1000000 + i * 500, // 500ms intervals
        timestamp_iso: new Date(1000000 + i * 500).toISOString(),
        layer: 'L1',
        event_type: i % 15 === 0 ? 'app_switch' : 'mouse_click',
        app_name: i < 20 ? 'chrome' : 'excel',
        process_name: i < 20 ? 'chrome.exe' : 'excel.exe',
        window_title: 'Title',
        clean_title: 'Title',
        extracted_case_ids: [],
        payload_summary: 'click',
      });
    }

    const bursts = formBursts(mockEvents, mockConfig, [], []);
    expect(bursts.length).toBeGreaterThan(1);

    // Sum of events across bursts must be exactly 45 (100% coverage)
    const totalCovered = bursts.reduce((acc, b) => acc + b.event_count, 0);
    expect(totalCovered).toBe(mockEvents.length);
  });

  it('strictly validates segment deliverable lines', () => {
    const valid = {
      session_id: 'ses_20260701-053720-SIDDHIGUPTAB00B',
      start: '2026-07-01T05:38:06Z',
      end: '2026-07-01T05:39:08Z',
      label: 'invoice_approval',
    };
    expect(() => SegmentLineSchema.parse(valid)).not.toThrow();

    // Extra keys must fail
    const invalidExtra = { ...valid, extra_field: 123 };
    expect(() => SegmentLineSchema.parse(invalidExtra)).toThrow();

    // Invalid ISO format must fail
    const invalidIso = { ...valid, start: '2026-07-01 05:38:06' };
    expect(() => SegmentLineSchema.parse(invalidIso)).toThrow();
  });
});
