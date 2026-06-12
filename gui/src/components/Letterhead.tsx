import type { GlossKey } from "../clarity";
import { Gloss } from "./Gloss";

/** The agency masthead (design law: full letterhead on every screen).
 * The crest is pure SVG; the docket line carries the open period. */
export function Crest({ size = 44 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 44 44"
      role="img"
      aria-label="Office of Seat Utilization Review crest"
    >
      <circle cx="22" cy="22" r="20" fill="none" stroke="currentColor" strokeWidth="2.5" />
      <circle cx="22" cy="22" r="15.5" fill="none" stroke="currentColor" strokeWidth="1" />
      <text
        x="22"
        y="20"
        textAnchor="middle"
        fontSize="9"
        fontFamily="var(--font-display)"
        fontWeight="900"
        fill="currentColor"
      >
        OSUR
      </text>
      <text x="22" y="31" textAnchor="middle" fontSize="9" fill="currentColor">
        ⚖
      </text>
    </svg>
  );
}

export function Letterhead({
  period,
  status,
  statusGloss,
}: {
  period: string;
  status: string;
  /** plain-language meaning for the status stamp (gui-14 clarity layer) */
  statusGloss?: GlossKey;
}) {
  return (
    <header
      className="letterhead"
    >
      <span className="ink">
        <Crest size={62} />
      </span>
      <div className="flex-1">
        <div className="t-title press">Office of Seat Utilization Review</div>
        <div className="eyebrow lh-sub">
          TOKEN-OPTIM · <Gloss term="docket">DOCKET</Gloss> NO. {period} ·{" "}
          {statusGloss ? <Gloss term={statusGloss}>{status}</Gloss> : status}
        </div>
      </div>
    </header>
  );
}
