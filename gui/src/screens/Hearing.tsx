import { useEffect, useMemo, useState } from "react";
import { SUBTITLES } from "../clarity";
import { EmptyState } from "../components/EmptyState";
import { Gloss } from "../components/Gloss";
import { EvidencePanel } from "../components/EvidencePanel";
import { ProductBadge } from "../components/ProductBadge";
import { RulesPanel } from "../components/RulesPanel";
import { SavingsMeter } from "../components/SavingsMeter";
import { VerdictRow } from "../components/VerdictRow";
import { SoundToggle } from "../components/SoundToggle";
import { Staple } from "../components/Staple";
import { VerdictStamp } from "../components/VerdictStamp";
import type { Product, Verdict } from "../domain";
import { projectedSavings } from "../domain";
import type { ClientRun } from "../store";
import { casesRemaining } from "../store";
import { vtName } from "../vt";

type Filter = "all" | Product;

/** Blueprint §3.2 — one case takes the stand at a time; the decided ledger
 * builds below. Keyboard: k/v/r decide the case on the stand. The seal
 * affordance is structurally disabled while cases remain (and the store
 * refuses regardless). */
export function Hearing({
  client,
  onVerdict,
  onAcceptAllSuggested,
  onRequestSeal,
  soundPersistent,
}: {
  client: ClientRun;
  onVerdict: (user: string, verdict: Verdict) => void;
  onAcceptAllSuggested: () => void;
  onRequestSeal: () => void;
  /** undefined = no sound toggle (bare stories); the App keys it to `persistent` */
  soundPersistent?: boolean;
}) {
  const [filter, setFilter] = useState<Filter>("all");
  const seats = client.seats ?? [];
  const visible = seats.filter((s) => filter === "all" || s.product === filter);
  const unheard = visible.filter((s) => !client.heard.includes(s.user));
  const decided = visible.filter((s) => client.heard.includes(s.user));
  const onStand = unheard[0];
  const remaining = casesRemaining(client);
  const meter = projectedSavings(seats); // the domain's exact arithmetic

  useEffect(() => {
    if (!onStand) return;
    const keys: Record<string, Verdict> = { k: "keep", v: "review", r: "reclaim" };
    const handler = (e: KeyboardEvent) => {
      const v = keys[e.key.toLowerCase()];
      if (v) onVerdict(onStand.user, v);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onStand, onVerdict]);

  const caseNumber = useMemo(
    () => seats.length - remaining + 1,
    [seats.length, remaining],
  );

  return (
    <main className="page">
      <header className="row-baseline">
        {/* inline-ok(data): shared-element vt name */}
        <h1 className="t-title press" style={{ viewTransitionName: vtName("tile", client.name) }}>
          {client.name} · {remaining > 0 ? `case ${caseNumber} of ${seats.length}` : "all cases heard"}
        </h1>
        <SavingsMeter monthlyUsd={meter} />
      </header>
      <p className="screen-sub" data-testid="screen-sub">
        {SUBTITLES.hearing}
      </p>
      <RulesPanel />

      <div role="group" aria-label="Product filter">
        {(["all", "m365", "github"] as const).map((f) => (
          <button
            key={f}
            aria-pressed={filter === f}
            onClick={() => setFilter(f)}
            className="mr-2"
          >
            {f === "all" ? "All" : <ProductBadge product={f} />}
          </button>
        ))}
        <button onClick={onAcceptAllSuggested} disabled={remaining === 0}>
          Accept all suggested ({remaining})
        </button>
      </div>

      {onStand ? (
        <section
          aria-label={`The case of ${onStand.user}`}
          data-testid="the-stand"
          className="sheet lies stand"
          /* inline-ok(data): per-instance tilt + shared-element vt name */
          style={{
            ["--lie-tilt" as string]: "0.4deg",
            // the flight: this case shares its name with its ledger row,
            // so verdicting it morphs the card INTO the row
            viewTransitionName: vtName("case", onStand.user),
          }}
        >
          <Staple />
          <div className="eyebrow">
            CASE FILE · {onStand.product === "m365" ? "M365" : "GITHUB"} COPILOT SEAT
          </div>
          <h2 className="t-title press case-title">
            The case of {onStand.user} <ProductBadge product={onStand.product} />
          </h2>
          <hr className="rule-double" />
          {/* the stand's evidence block is register-free (blueprint §3.2) */}
          <EvidencePanel seat={onStand} />
          <p className="muted">
            the committee suggests:{" "}
            <VerdictStamp verdict={onStand.verdict} seed={`${onStand.user}|suggested`} />
          </p>
          <p>
            {([["k", "keep"], ["v", "review"], ["r", "reclaim"]] as const).map(([key, v]) => (
              <button
                key={v}
                onClick={() => onVerdict(onStand.user, v)}
                className="mr-2"
              >
                [{key}] {v}
              </button>
            ))}
          </p>
        </section>
      ) : (
        <p role="status" className="my-6">
          All cases heard. The docket is ready to seal.
        </p>
      )}

      <section aria-label="The ledger">
        <h2 className="t-label section-head">
          <span>
            <Gloss term="ledger">The ledger</Gloss>
          </span>
          <span className="t-figure muted">{decided.length} decided</span>
        </h2>
        {decided.length === 0 && (
          <EmptyState
            what="No decisions yet"
            how="Each seat you decide on the stand above lands here as a ledger row, stamped with its verdict."
          />
        )}
        <table className="ledger">
          <tbody>
            {decided.map((s) => (
              <VerdictRow
                key={`${s.product}:${s.user}`}
                seat={s}
                plain={decided.length > 50}
                onVerdict={(v) => onVerdict(s.user, v)}
              />
            ))}
          </tbody>
        </table>
      </section>

      <footer className="mt-6">
        {soundPersistent !== undefined && (
          <span className="mr-2">
            <SoundToggle persistent={soundPersistent} />
          </span>
        )}
        <button
          onClick={onRequestSeal}
          disabled={remaining > 0}
          data-testid="seal-button"
          className={remaining > 0 ? "btn-lg" : "btn-primary btn-lg"}
        >
          {remaining > 0
            ? `${remaining} cases remaining — hear all to unlock`
            : `Seal report for ${client.name} ⟶`}
        </button>
      </footer>
    </main>
  );
}
