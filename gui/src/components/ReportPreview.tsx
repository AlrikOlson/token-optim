import type { Seat } from "../domain";
import { projectedSavings } from "../domain";
import { BrandChip } from "./BrandChip";
import { CaveatBlock } from "./CaveatBlock";

/** The client deliverable's frame (blueprint §3.3). HARD REGISTER
 * BOUNDARY: this component must never import the voice engine — it renders
 * only plain, stated-rule language, exactly like demo.py's render_report. */
export function ReportPreview({
  seats,
  mspName,
  clientName,
  accent = "#1f6feb",
  caveats,
}: {
  seats: readonly Seat[];
  mspName: string;
  clientName: string;
  accent?: string;
  caveats: readonly string[];
}) {
  const monthly = projectedSavings(seats);
  const counts = {
    reclaim: seats.filter((s) => s.verdict === "reclaim").length,
    review: seats.filter((s) => s.verdict === "review").length,
    keep: seats.filter((s) => s.verdict === "keep").length,
  };
  return (
    <article
      className="report-preview sheet report-sheet"
      aria-label={`Right-sizing report for ${clientName}`}
    >
      <h2
        className="t-title press"
        /* inline-ok(data): the rule is drawn in the MSP's brand ink */
        style={{ borderBottom: `4px double ${accent}`, paddingBottom: "var(--space-2)" }}
      >
        AI License Right-Sizing Report
      </h2>
      <p className="muted">
        Prepared for <strong>{clientName}</strong> by <BrandChip mspName={mspName} accent={accent} />{" "}
        · {seats.length} Copilot seats analyzed
      </p>
      <p className="lead">
        Projected savings:{" "}
        <strong className="t-figure savings press" data-testid="report-savings">
          ${monthly.toLocaleString("en-US", { maximumFractionDigits: 0 })}/month
        </strong>{" "}
        — {counts.reclaim} seats to reclaim, {counts.review} to review,{" "}
        {counts.keep} actively used.
      </p>
      <table className="ledger">
        <thead>
          <tr>
            <th>User</th>
            <th>Verdict</th>
            <th>Why</th>
          </tr>
        </thead>
        <tbody>
          {seats.map((s) => (
            <tr key={`${s.product}:${s.user}`}>
              <td>{s.user}</td>
              <td>{s.verdict}</td>
              {/* plain stated-rule reason — never the Committee register */}
              <td className="mono muted evidence">{s.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <CaveatBlock caveats={caveats} />
    </article>
  );
}
