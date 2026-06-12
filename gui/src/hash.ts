/** FNV-1a — the project's one deterministic hash (no Math.random anywhere:
 * stamp tilts and voice rotation must be reproducible per payload).
 * Iterates UTF-16 code units; demo.py's _fnv1a mirrors this exactly so the
 * same seat stamps identically on the Python report and the GUI (gui-11). */
export function stableHash(s: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h;
}

/** The canonical stamp tilt: ±2° in 0.5° steps from FNV-1a(`seed|stamp`).
 * Shared verbatim (algorithm + input string) with demo.py:_stamp_tilt. */
export function stampTilt(seed: string): number {
  return ((stableHash(`${seed}|stamp`) % 9) - 4) * 0.5;
}

/** Which of InkBleedDefs' seeded erosion filters this impression wears —
 * a different worn pad per stamp, still deterministic per seed (gui-11). */
export function erosionVariant(seed: string, variants: number): number {
  return stableHash(`${seed}|erosion`) % variants;
}
