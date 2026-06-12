import { useState } from "react";
import { APP_PURPOSE, dismissFirstRun, firstRunDismissed } from "../clarity";

/** The first-run explainer (gui-14): two true sentences on the Run Board,
 * plain register, dismissable. `persistent` follows the App's discipline —
 * true in the real app (dismissal survives reload via localStorage), false
 * under an explicit initial state so stories and tests stay deterministic
 * (always shows; dismissal lasts the session). */
export function FirstRunSlip({ persistent = true }: { persistent?: boolean }) {
  const [dismissed, setDismissed] = useState(() => (persistent ? firstRunDismissed() : false));
  if (dismissed) return null;
  return (
    <aside className="slip first-run" data-testid="first-run" aria-label="What this tool does">
      <p className="m-0">{APP_PURPOSE}</p>
      <button
        onClick={() => {
          if (persistent) dismissFirstRun();
          setDismissed(true);
        }}
        data-testid="first-run-dismiss"
        className="mt-2"
      >
        Got it — don't show this again
      </button>
    </aside>
  );
}
