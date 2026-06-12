export interface SnapshotPointData {
  period: string; // YYYY-MM
  savingsUsd: number;
  sealed: boolean;
}

/** One sealed month on the history strip (blueprint §3.4). Unsealed drafts
 * render visibly provisional — they can never be confused with the record. */
export function SnapshotPoint({ snapshot }: { snapshot: SnapshotPointData }) {
  return (
    <span
      className="snapshot-point t-figure"
      data-sealed={snapshot.sealed}
    >
      {snapshot.period}{" "}
      {snapshot.sealed
        ? `$${snapshot.savingsUsd.toLocaleString("en-US", { maximumFractionDigits: 0 })} ✓`
        : "(draft)"}
    </span>
  );
}
