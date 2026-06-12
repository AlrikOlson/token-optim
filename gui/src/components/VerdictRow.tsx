import type { Seat, Verdict } from "../domain";
import { evidenceLine, plainEvidence, type EvidencePayload } from "../voice";
import { ProductBadge } from "./ProductBadge";
import { VerdictStamp } from "./VerdictStamp";
import { vtName } from "../vt";

export function evidencePayload(seat: Seat): EvidencePayload | null {
  // Voice restraint: reclaim rows only, and only when the EVIDENCE itself
  // is reclaim-grade (never used, or idle past the stated 45-day rule).
  // A reviewer override of an active seat gets plain language — the wry
  // line must never outrun its backing truth (gui-3 scrutiny finding).
  if (seat.verdict !== "reclaim") return null;
  if (seat.daysSinceLastActivity === null) {
    return { kind: "never-used", user: seat.user, seatCostUsd: seat.monthlySavingUsd };
  }
  if (seat.daysSinceLastActivity > 45) {
    return {
      kind: "idle",
      user: seat.user,
      idleDays: seat.daysSinceLastActivity,
      seatCostUsd: seat.monthlySavingUsd,
    };
  }
  return null;
}

/** Compact ledger form of a SeatRecommendation (blueprint §4). Every decided
 * case carries its rubber stamp (design law). The wry line appears only on
 * reclaim rows with rule-grade evidence, via the voice engine's payload API;
 * `plain` switches to the register-free fallback (high row counts). */
export function VerdictRow({
  seat,
  plain = false,
  onVerdict,
}: {
  seat: Seat;
  plain?: boolean;
  onVerdict?: (v: Verdict) => void;
}) {
  const payload = evidencePayload(seat);
  const evidence = payload
    ? (plain ? plainEvidence : evidenceLine)(payload)
    : seat.reason;
  const saving = seat.monthlySavingUsd;
  return (
    <tr
      className="verdict-row"
      data-verdict={seat.verdict}
      /* inline-ok(data): shared with the stand — a decided case flies into this row */
      style={{ viewTransitionName: vtName("case", seat.user) }}
    >
      <td className="mono">
        <ProductBadge product={seat.product} /> {seat.user}
      </td>
      <td className="evidence mono muted">{evidence}</td>
      <td className="nowrap">
        <VerdictStamp verdict={seat.verdict} seed={seat.user} />
        {onVerdict && (
          <select
            aria-label={`Verdict for ${seat.user}`}
            value={seat.verdict}
            onChange={(e) => onVerdict(e.target.value as Verdict)}
            className="ml-2"
          >
            <option value="keep">keep</option>
            <option value="review">review</option>
            <option value="reclaim">reclaim</option>
          </select>
        )}
      </td>
      <td className="num t-figure" data-testid="row-saving">
        {saving > 0 ? `+$${saving.toLocaleString("en-US", { maximumFractionDigits: 2 })}` : "—"}
      </td>
    </tr>
  );
}
