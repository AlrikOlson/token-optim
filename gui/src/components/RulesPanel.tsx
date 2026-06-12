import { Fragment } from "react";
import { RULES_SPEC } from "../rules";

const VERDICT_INK: Record<string, string> = {
  keep: "var(--verdict-keep)",
  review: "var(--verdict-review)",
  reclaim: "var(--verdict-reclaim)",
};

/** The stated rules, on the record (gui-15). Rendered from RULES_SPEC —
 * the same generated spec the suggestion engine decides with (gui-1b) —
 * so this panel cannot state a rule the engine doesn't apply. Plain
 * register: these are the exact lines the client report prints under
 * "How verdicts are decided". Design law: no VerdictStamp here — stamps
 * render true verdict values, never examples. */
export function RulesPanel({ defaultOpen = false }: { defaultOpen?: boolean }) {
  return (
    <details className="rules-panel" open={defaultOpen} data-testid="rules-panel">
      <summary className="t-label">How verdicts are decided</summary>
      <p className="screen-sub">
        The committee suggests each verdict by these stated rules — the same
        rules printed in the client report. You decide every case; any
        suggestion can be overridden.
      </p>
      <dl className="evidence-panel">
        {RULES_SPEC.stated.map(({ verdict, description }) => (
          <Fragment key={verdict}>
            {/* inline-ok(data): verdict ink */}
            <dt style={{ color: VERDICT_INK[verdict] }}>{verdict}</dt>
            <dd>{description}</dd>
          </Fragment>
        ))}
      </dl>
    </details>
  );
}
