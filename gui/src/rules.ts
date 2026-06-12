/** The client-side stated rules, driven by ./rules-spec.json — GENERATED
 * from advisory.py (`python3 advisory.py > gui/src/rules-spec.json`), which
 * stays the single authoritative statement of the rules. A pytest drift
 * gate keeps the artifact equal to advisory.rules_spec(), and golden
 * vectors in BOTH suites keep the two interpreters in behavioral lockstep
 * (gui-1b). Reason PROSE intentionally differs per surface (the report says
 * "never used Copilot" for CSV provenance; the GUI says NO_RECORD_PHRASE). */

import type { Product, Seat, Verdict } from "./domain";
import spec from "./rules-spec.json";

export const RULES_SPEC = spec;
const T = spec.thresholds;

export interface SeatActivity {
  user: string;
  product: Product;
  /** null = no activity on record (vendor retains ~90 days). */
  daysSinceLastActivity: number | null;
  activeApps?: number;
  appsTracked?: boolean;
}

export const NO_RECORD_PHRASE = "no activity on record (vendor retains 90 days)";

export function suggestVerdict(a: SeatActivity): {
  verdict: Verdict;
  reason: string;
} {
  if (a.daysSinceLastActivity === null) {
    return { verdict: "reclaim", reason: NO_RECORD_PHRASE };
  }
  if (a.daysSinceLastActivity > T.reclaim_after_days) {
    return {
      verdict: "reclaim",
      reason: `inactive ${a.daysSinceLastActivity} days`,
    };
  }
  if (
    a.daysSinceLastActivity > T.review_after_days ||
    (a.appsTracked && (a.activeApps ?? 0) <= T.single_app_max)
  ) {
    return {
      verdict: "review",
      reason:
        `last active ${a.daysSinceLastActivity}d ago` +
        (a.appsTracked ? `, ${a.activeApps} app(s) in the last month` : ""),
    };
  }
  return {
    verdict: "keep",
    reason: a.appsTracked
      ? `active, ${a.activeApps} apps in the last month`
      : `active ${a.daysSinceLastActivity}d ago`,
  };
}

export function suggestedSeat(a: SeatActivity, seatCostUsd: number): Seat {
  const { verdict, reason } = suggestVerdict(a);
  return {
    user: a.user,
    product: a.product,
    verdict,
    reason,
    monthlySavingUsd: verdict === "reclaim" ? seatCostUsd : 0,
    daysSinceLastActivity: a.daysSinceLastActivity,
    activeApps: a.activeApps,
  };
}
