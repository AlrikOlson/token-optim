import type { Seat } from "../domain";

/** Register-free evidence (blueprint §3.2): raw counts, dates, the citing
 * rule. This is the auditable layer under any wry summary — it must never
 * import the voice engine. */
export function EvidencePanel({ seat }: { seat: Seat }) {
  const activity =
    seat.daysSinceLastActivity === null
      ? "no activity on record (vendor retains 90 days)"
      : `last activity ${seat.daysSinceLastActivity} days ago`;
  return (
    <dl className="evidence-panel mono">
      <dt>activity</dt>
      <dd data-testid="evidence-activity">{activity}</dd>
      {seat.activeApps !== undefined && (
        <>
          <dt>apps in last month</dt>
          <dd>{seat.activeApps}</dd>
        </>
      )}
      <dt>cited rule</dt>
      <dd data-testid="evidence-rule">{seat.reason}</dd>
      <dt>monthly cost consequence</dt>
      <dd>
        {seat.monthlySavingUsd > 0
          ? `$${seat.monthlySavingUsd.toFixed(2)} reclaimable`
          : "none at current verdict"}
      </dd>
    </dl>
  );
}
