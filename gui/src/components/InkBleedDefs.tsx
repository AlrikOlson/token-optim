/** SVG filters shared by every .stamp — the ink-bleed edge that makes a
 * rubber stamp read as rubber. Mount once per document (App + Storybook).
 *
 * gui-11 (The Print Shop): eight seeded variants, #ink-bleed-0..7 — each a
 * differently worn pad (feTurbulence seed + displacement jitter), so two
 * stamps never erode identically. VerdictStamp picks one deterministically
 * via erosionVariant(); #ink-bleed stays as the unseeded default for any
 * .stamp outside that path. */
export const EROSION_VARIANTS = 8;

function pad(i: number) {
  // worn pads differ in seed and, slightly, in how far the edge rags out
  const edgeSeed = i * 7 + 3;
  const padSeed = i * 13 + 5;
  const scale = (1.5 + (i % 4) * 0.12).toFixed(2);
  return (
    <filter id={`ink-bleed-${i}`} key={i}>
      <feTurbulence type="fractalNoise" baseFrequency="0.08" numOctaves="2" seed={edgeSeed} result="edge" />
      <feDisplacementMap in="SourceGraphic" in2="edge" scale={scale} result="shaped" />
      <feTurbulence type="fractalNoise" baseFrequency="0.45" numOctaves="2" seed={padSeed} result="pad" />
      <feColorMatrix in="pad" type="matrix"
        values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1.6 -0.25" result="padAlpha" />
      <feComposite in="shaped" in2="padAlpha" operator="in" />
    </filter>
  );
}

export function InkBleedDefs() {
  return (
    <svg width="0" height="0" className="svg-defs" aria-hidden="true">
      <filter id="ink-bleed">
        {/* photoreal pad ink: ragged edge AND uneven coverage — turbulence
            displaces the outline, then a second noise erodes the ink body
            the way a worn rubber pad under-inks (gui-6). */}
        <feTurbulence type="fractalNoise" baseFrequency="0.08" numOctaves="2" result="edge" />
        <feDisplacementMap in="SourceGraphic" in2="edge" scale="1.7" result="shaped" />
        <feTurbulence type="fractalNoise" baseFrequency="0.45" numOctaves="2" result="pad" />
        <feColorMatrix in="pad" type="matrix"
          values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1.6 -0.25" result="padAlpha" />
        <feComposite in="shaped" in2="padAlpha" operator="in" />
      </filter>
      {Array.from({ length: EROSION_VARIANTS }, (_, i) => pad(i))}
    </svg>
  );
}
