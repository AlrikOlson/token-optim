/** THE CLARITY LAYER (gui-14, UX mandate: "understand instantly").
 *
 * One module owns ALL plain-register explanation copy. The Federal Memo
 * voice is the brand; this layer sits UNDER it so a first-time viewer can
 * answer "what does this app do, and what do I do next" from any screen.
 *
 * Register rules: sentence case, no parody, no exclamation marks, every
 * sentence is literally true of the running app. The client-facing report
 * layer may import this module (it is register-safe); voice.ts may not.
 */

/** Two true sentences. Shown once on the Run Board until dismissed. */
export const APP_PURPOSE =
  "This tool finds paid Microsoft 365 and GitHub Copilot seats that nobody is using, " +
  "and turns them into a monthly savings report for each client. " +
  "Open a client, confirm or change each suggested decision, then seal the month to lock the report.";

/** Plain one-liners under each screen's masthead. */
export const SUBTITLES = {
  board:
    "One card per client this month. Open a card to review its seats; sealed cards are finished.",
  hearing:
    "Review each seat's usage evidence and pick keep, review, or reclaim. Decide every seat to unlock the seal.",
  seal:
    "Final check. Sealing locks this month's report permanently and files it in the client's record.",
  archive:
    "A sealed month, exactly as delivered. Read-only — history never changes here.",
  qbr: "A quarterly summary for this client, built only from sealed monthly reports.",
} as const;

export type ScreenKey = keyof typeof SUBTITLES;

/** Every Memo-register term a first-time viewer meets, with its plain
 * meaning. Glosses render via the Gloss component — single source. */
export const GLOSSARY = {
  "in-session": "This month is still open: decisions can still be made.",
  "awaiting-data": "No usage export has been loaded for this client yet.",
  "verdicts-in": "Suggested decisions are ready; nothing has been reviewed yet.",
  "in-review": "Someone is working through this client's seats.",
  sealed: "The month is finished: its report is locked and delivered.",
  verdict: "The decision for one seat: keep it, review it later, or reclaim (cancel) it.",
  keep: "The seat is in use — keep paying for it.",
  review: "Unclear — check with the user before deciding.",
  reclaim: "The seat is unused — cancel it and stop paying.",
  hearing: "The review screen: one seat at a time, with its usage evidence.",
  seal: "Locking a finished month so its report can never change.",
  docket: "The list of seats still waiting for a decision this month.",
  qbr: "Quarterly business review — the summary MSPs present to clients every quarter.",
  exhibit: "The saved history of past sealed months.",
  ledger: "The running list of seats already decided this month.",
} as const;

export type GlossKey = keyof typeof GLOSSARY;

/** localStorage key for the first-run dismissal (versioned like the store). */
export const FIRST_RUN_KEY = "token-optim:first-run-dismissed:v1";

export function firstRunDismissed(): boolean {
  try {
    return globalThis.localStorage?.getItem(FIRST_RUN_KEY) === "true";
  } catch {
    return false;
  }
}

export function dismissFirstRun(): void {
  try {
    globalThis.localStorage?.setItem(FIRST_RUN_KEY, "true");
  } catch {
    /* storage unavailable — dismissal lasts the session only */
  }
}
