/** The embossed seal pressed onto a sealed record (design law: the one
 * ceremony artifact). Pure SVG emboss: highlight ring above, shadow ring
 * below, no color — pressure, not ink. */
export function SealCrest({ period, size = 110 }: { period: string; size?: number }) {
  return (
    <svg
      className="seal-crest"
      width={size}
      height={size}
      viewBox="0 0 110 110"
      role="img"
      aria-label={`Sealed, ${period}`}
    >
      <defs>
        <filter id="emboss">
          <feDropShadow dx="0" dy="1" stdDeviation="0.6" floodColor="rgba(255,255,255,0.65)" />
          <feDropShadow dx="0" dy="-1" stdDeviation="0.6" floodColor="rgba(33,29,22,0.45)" />
        </filter>
      </defs>
      <g filter="url(#emboss)" fill="none" stroke="var(--ink-muted)" opacity="0.7">
        <circle cx="55" cy="55" r="50" strokeWidth="3" />
        <circle cx="55" cy="55" r="40" strokeWidth="1.2" />
        <path id="seal-arc" d="M 55 20 A 35 35 0 1 1 54.9 20" />
        <text fontSize="10.5" fontFamily="var(--font-display)" fontWeight="900" letterSpacing="2.5" fill="var(--ink-muted)" stroke="none">
          <textPath href="#seal-arc" startOffset="0%">
            SEALED · PERMANENT RECORD · {period} ·
          </textPath>
        </text>
        <text
          x="55"
          y="61"
          textAnchor="middle"
          fontSize="20"
          fill="var(--ink-muted)"
          stroke="none"
        >
          ⚖
        </text>
      </g>
    </svg>
  );
}
