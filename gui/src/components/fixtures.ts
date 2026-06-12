/** Shared story fixtures — real domain shapes from the fabrikam-demo org
 * (same population as demo.py's sample_csv). Never lorem ipsum. */
import type { Seat } from "../domain";

export const seats: Seat[] = [
  {
    user: "maria.chen@fabrikam-demo.com",
    product: "m365",
    verdict: "keep",
    reason: "active, 3 apps in the last month",
    monthlySavingUsd: 0,
    daysSinceLastActivity: 2,
    activeApps: 3,
  },
  {
    user: "raj.kumar@fabrikam-demo.com",
    product: "m365",
    verdict: "review",
    reason: "last active 22d ago, 1 app(s) in the last month",
    monthlySavingUsd: 0,
    daysSinceLastActivity: 22,
    activeApps: 1,
  },
  {
    user: "mark.olsen@fabrikam-demo.com",
    product: "m365",
    verdict: "reclaim",
    reason: "inactive 92 days",
    monthlySavingUsd: 30,
    daysSinceLastActivity: 92,
  },
  {
    user: "bob.tanner@fabrikam-demo.com",
    product: "m365",
    verdict: "reclaim",
    reason: "never used Copilot",
    monthlySavingUsd: 30,
    daysSinceLastActivity: null,
  },
  {
    user: "dev-eng-04",
    product: "github",
    verdict: "reclaim",
    reason: "inactive 80 days",
    monthlySavingUsd: 19,
    daysSinceLastActivity: 80,
  },
];

export const caveats = [
  "Activity data from the Microsoft 365 Copilot usage report; no message content is accessed.",
  "GitHub last-activity is retained ~90 days by the vendor; sealed snapshots preserve history beyond that window.",
];
