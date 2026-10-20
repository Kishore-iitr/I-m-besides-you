import { RawEvent, TypedText } from '../types.js';

export interface KeystrokeRunBuffer {
  ts_start: number;
  ts_end: number;
  app: string;
  field: string;
  characters: string[];
  rawKeys: string[];
  hadBackspace: boolean;
  ime_suspected: boolean;
}

/**
 * Reconstruct typed strings per (app, field) run.
 * Honours backspace, enter, tab, and modifiers.
 * Emits TypedText { ts_start, ts_end, app, field, text, confidence, ime_suspected }.
 * Does not rely on text_input_complete.
 */
export function reconstructKeystrokes(
  events: RawEvent[],
  idleThresholdMs: number = 1500
): TypedText[] {
  const typedTexts: TypedText[] = [];

  let currentRun: KeystrokeRunBuffer | null = null;

  function flushRun() {
    if (!currentRun || currentRun.characters.length === 0) {
      currentRun = null;
      return;
    }

    const text = currentRun.characters.join('');
    if (text.trim().length > 0) {
      // Calculate confidence: base 0.95; lower slightly if frequent backspacing or suspected IME
      let confidence = 0.95;
      if (currentRun.hadBackspace) confidence -= 0.05;
      if (currentRun.ime_suspected) confidence -= 0.05;

      typedTexts.push({
        ts_start: currentRun.ts_start,
        ts_end: currentRun.ts_end,
        app: currentRun.app,
        field: currentRun.field,
        text,
        confidence: Number(Math.max(0.5, confidence).toFixed(2)),
        ime_suspected: currentRun.ime_suspected,
      });
    }

    currentRun = null;
  }

  for (const ev of events) {
    if (ev.event_type !== 'keystroke') {
      // If we encounter a mouse click or app switch, flush active typing run
      if (ev.event_type === 'mouse_click' || ev.event_type === 'app_switch') {
        flushRun();
      }
      continue;
    }

    const app = (
      ev.context?.active_app?.process_name ||
      ev.payload?.app_name ||
      'unknown'
    ).trim();

    const field = (
      ev.payload?.target_element?.name ||
      ev.payload?.target_element?.automation_id ||
      ev.payload?.field ||
      ev.payload?.target_element?.control_type ||
      'general_input'
    ).trim();

    const timeMs = ev.timestamp_ms;
    const key = String(ev.payload?.key || '');
    const character = ev.payload?.character;
    const modifiers = ev.payload?.modifiers || [];

    // Check if run should be broken: different app, different field, or idle timeout
    if (
      currentRun &&
      (currentRun.app !== app ||
        currentRun.field !== field ||
        timeMs - currentRun.ts_end > idleThresholdMs)
    ) {
      flushRun();
    }

    if (!currentRun) {
      currentRun = {
        ts_start: timeMs,
        ts_end: timeMs,
        app,
        field,
        characters: [],
        rawKeys: [],
        hadBackspace: false,
        ime_suspected: false,
      };
    }

    currentRun.ts_end = timeMs;
    currentRun.rawKeys.push(key);

    // Modifier check
    const isModifierKey = /^Key\.(shift|ctrl|alt|meta|cmd|super)/i.test(key) ||
      ['Shift', 'Control', 'Alt', 'Meta', 'CapsLock'].includes(key);

    if (isModifierKey) {
      continue;
    }

    // Japanese IME detection heuristic:
    // Repeated romaji consonant keys followed by Henkan/Muhenkan/Kana or Kanji conversions
    if (/^(henkan|muhenkan|hiragana|katakana|zenkaku_hankaku)$/i.test(key)) {
      currentRun.ime_suspected = true;
      continue;
    }

    // Process character / editing action
    if (key === 'Backspace' || key === 'Key.backspace') {
      currentRun.hadBackspace = true;
      if (currentRun.characters.length > 0) {
        currentRun.characters.pop();
      }
    } else if (key === 'Enter' || key === 'Return' || key === 'Key.enter') {
      currentRun.characters.push('\n');
    } else if (key === 'Tab' || key === 'Key.tab') {
      currentRun.characters.push('\t');
    } else if (key === 'Space' || key === 'Key.space') {
      currentRun.characters.push(' ');
    } else if (typeof character === 'string' && character.length === 1) {
      currentRun.characters.push(character);
    } else if (key.length === 1) {
      // Direct single character
      currentRun.characters.push(key);
    } else if (/^Key\.([a-zA-Z0-9])$/.test(key)) {
      const match = key.match(/^Key\.([a-zA-Z0-9])$/);
      if (match) {
        currentRun.characters.push(match[1]);
      }
    }
  }

  flushRun();
  return typedTexts;
}
