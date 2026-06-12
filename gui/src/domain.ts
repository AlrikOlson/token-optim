/** Domain shapes mirroring the Python dataclasses (ledger.py / advisory.py).
 * The GUI renders these; it never invents figures of its own. */

export type Product = "m365" | "github";

export type Verdict = "keep" | "review" | "reclaim";

/** advisory.SeatRecommendation + the activity evidence behind it. */
export interface Seat {
  user: string;
  product: Product;
  verdict: Verdict;
  /** Stated-rule explanation from advisory.py — already true by construction. */
  reason: string;
  /** Exactly advisory's monthly_saving_usd; reclaim => seat cost, else 0. */
  monthlySavingUsd: number;
  /** null = no activity on record (vendor retains ~90 days). */
  daysSinceLastActivity: number | null;
  activeApps?: number;
}

export type ClientStage = "awaiting-data" | "verdicts-in" | "in-review" | "sealed";

/** Run Board tile state — derived from pipeline events, never hand-set. */
export interface ClientTileData {
  name: string;
  stage: ClientStage;
  /** Present only when sealed: the period's projected_savings(). */
  sealedSavingsUsd?: number;
  /** Cases left to hear (in-review stage). */
  casesRemaining?: number;
  /** True figures from the client's seat data (gui-6c): the tile is an
   * index card that says something. */
  stats?: {
    seats: number;
    reclaimSuggested: number;
    potentialUsd: number;
  };
}

/** Sum of per-seat savings — the same arithmetic as advisory.projected_savings. */
export function projectedSavings(seats: readonly Seat[]): number {
  return seats.reduce((s, r) => s + r.monthlySavingUsd, 0);
}
