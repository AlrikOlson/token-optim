/** THE OFFICE SPEAKS (Saga Act IV, gui-10).
 *
 * Pure Web Audio synthesis — no samples. The values-never-lie rule extends
 * to ears: each voice below fires ONLY from a real domain event handler
 * (verdict, card flight, seal confirm, docket advance), never decoratively.
 *
 * Discipline:
 * - OFF by default; the visible SoundToggle flips it; preference persists
 *   under the same versioned-key convention as the store.
 * - prefers-reduced-motion suppresses ALL sound (proxy until the audio
 *   preference media query lands).
 * - The AudioContext is created lazily INSIDE a user-gesture handler and
 *   defensively resume()d (Chrome autoplay policy; MDN best practices).
 * - Deliverable contexts must never import this module — enforced by
 *   sound.test.ts the same way the report register is enforced.
 */

export const SOUND_KEY = "token-optim:sound:v1";

export type OfficeSound = "stamp" | "shuffle" | "seal" | "tick";

let enabled = false;
let ctx: AudioContext | null = null;

export function soundEnabled(): boolean {
  return enabled;
}

/** Restore the persisted preference (the App calls this once when running
 * in persistent mode; stories/tests skip it and stay deterministic). */
export function restoreSoundPreference(): void {
  try {
    enabled = globalThis.localStorage?.getItem(SOUND_KEY) === "true";
  } catch {
    enabled = false;
  }
}

export function setSoundEnabled(on: boolean, persist: boolean): void {
  enabled = on;
  if (persist) {
    try {
      globalThis.localStorage?.setItem(SOUND_KEY, String(on));
    } catch {
      /* storage unavailable — preference lasts the session */
    }
  }
}

function reducedMotion(): boolean {
  return globalThis.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches ?? false;
}

function audioContext(): AudioContext | null {
  if (ctx) return ctx;
  const Ctor = (globalThis as { AudioContext?: typeof AudioContext }).AudioContext;
  if (!Ctor) return null; // jsdom / ancient browsers: silently no-op
  ctx = new Ctor();
  return ctx;
}

/** White-noise buffer, cached per context. */
let noiseBuffer: AudioBuffer | null = null;
function noise(c: AudioContext): AudioBuffer {
  if (noiseBuffer) return noiseBuffer;
  const buf = c.createBuffer(1, c.sampleRate * 0.4, c.sampleRate);
  const data = buf.getChannelData(0);
  for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
  noiseBuffer = buf;
  return buf;
}

function noiseBurst(
  c: AudioContext,
  t: number,
  { dur, type, freq, q, gain }: { dur: number; type: BiquadFilterType; freq: number; q: number; gain: number },
) {
  const src = c.createBufferSource();
  src.buffer = noise(c);
  const filter = c.createBiquadFilter();
  filter.type = type;
  filter.frequency.value = freq;
  filter.Q.value = q;
  const g = c.createGain();
  g.gain.setValueAtTime(gain, t);
  g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  src.connect(filter).connect(g).connect(c.destination);
  src.start(t);
  src.stop(t + dur);
}

function thump(
  c: AudioContext,
  t: number,
  { from, to, dur, gain }: { from: number; to: number; dur: number; gain: number },
) {
  const osc = c.createOscillator();
  osc.type = "sine";
  osc.frequency.setValueAtTime(from, t);
  osc.frequency.exponentialRampToValueAtTime(to, t + dur);
  const g = c.createGain();
  g.gain.setValueAtTime(gain, t);
  g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  osc.connect(g).connect(c.destination);
  osc.start(t);
  osc.stop(t + dur);
}

/** Play one office sound. No-op when disabled, reduced-motion, or no
 * Web Audio. Must only ever be called from a user-gesture-driven domain
 * event handler — that is both the design law and the autoplay contract. */
export function playSound(sound: OfficeSound): void {
  if (!enabled || reducedMotion()) return;
  const c = audioContext();
  if (!c) return;
  if (c.state === "suspended") void c.resume();
  const t = c.currentTime;
  switch (sound) {
    case "stamp": // the rubber stamp: felt strike + low wood thunk
      noiseBurst(c, t, { dur: 0.06, type: "bandpass", freq: 1800, q: 1.2, gain: 0.25 });
      thump(c, t, { from: 140, to: 70, dur: 0.12, gain: 0.5 });
      break;
    case "shuffle": // a sheet sliding across the desk
      noiseBurst(c, t, { dur: 0.16, type: "bandpass", freq: 4200, q: 0.8, gain: 0.12 });
      break;
    case "seal": // the heavier press: deeper, longer, with paper crunch
      noiseBurst(c, t, { dur: 0.12, type: "lowpass", freq: 900, q: 0.7, gain: 0.3 });
      thump(c, t, { from: 110, to: 50, dur: 0.3, gain: 0.7 });
      break;
    case "tick": // one typewriter tick on the docket counter
      noiseBurst(c, t, { dur: 0.025, type: "highpass", freq: 3000, q: 1, gain: 0.18 });
      break;
  }
}

/** Test seam: reset module state (unit tests only). */
export function _resetSoundForTests(): void {
  enabled = false;
  ctx = null;
  noiseBuffer = null;
}
