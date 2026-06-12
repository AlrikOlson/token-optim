import type { SnapshotPointData } from "./SnapshotPoint";
import { SnapshotPoint } from "./SnapshotPoint";

/** Quarterly rollup (blueprint §3.5). The invariant is mechanical: this
 * component THROWS if handed any unsealed period — unsealed data cannot
 * appear in a QBR pack even by programmer mistake. */
export function QBRPack({
  clientName,
  quarter,
  snapshots,
}: {
  clientName: string;
  quarter: string; // e.g. "Q2 2026"
  snapshots: readonly SnapshotPointData[];
}) {
  const unsealed = snapshots.filter((s) => !s.sealed);
  if (unsealed.length > 0) {
    throw new Error(
      `QBRPack composes sealed snapshots only; unsealed: ${unsealed
        .map((s) => s.period)
        .join(", ")}`,
    );
  }
  const total = snapshots.reduce((t, s) => t + s.savingsUsd, 0);
  return (
    <section
      className="qbr-pack"
      aria-label={`${quarter} QBR pack for ${clientName}`}
    >
      <h3 className="t-title press">
        {clientName} · {quarter} QBR pack
      </h3>
      <p>
        {snapshots.map((s) => (
          <SnapshotPoint key={s.period} snapshot={s} />
        ))}
      </p>
      <p>
        Quarter story:{" "}
        <strong className="t-figure-lg savings press" data-testid="qbr-total">
          ${total.toLocaleString("en-US", { maximumFractionDigits: 0 })}
        </strong>{" "}
        identified across {snapshots.length} sealed month
        {snapshots.length === 1 ? "" : "s"}.
      </p>
    </section>
  );
}
