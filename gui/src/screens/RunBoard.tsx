import { SUBTITLES } from "../clarity";
import { ClientTile } from "../components/ClientTile";
import { EmptyState } from "../components/EmptyState";
import { FirstRunSlip } from "../components/FirstRunSlip";
import { Gloss } from "../components/Gloss";
import { Letterhead } from "../components/Letterhead";
import { SoundToggle } from "../components/SoundToggle";
import { projectedSavings } from "../domain";
import type { AppState, Stage } from "../store";
import { decorativeSeatPct, casesRemaining, quarterOf, runTally, stageOf } from "../store";
import { ambientLine, exhibitCaption, milestoneLine } from "../voice";

const COLUMNS: { stage: Stage; title: string }[] = [
  { stage: "awaiting-data", title: "Awaiting data" },
  { stage: "verdicts-in", title: "Verdicts in" },
  { stage: "in-review", title: "In review" },
  { stage: "sealed", title: "Sealed & delivered" },
];

/** Blueprint §3.1 — the monthly run. Tile position is derived from
 * pipeline state; there is deliberately no drag affordance. */
export function RunBoard({
  state,
  onOpenClient,
  onOpenQBR,
  firstRunPersistent,
  soundPersistent,
}: {
  state: AppState;
  onOpenClient: (clientId: string) => void;
  onOpenQBR?: (clientId: string, quarter: string) => void;
  /** undefined = no explainer (bare screen stories); the App always passes
   * a value and keys persistence to its own `persistent` discipline */
  firstRunPersistent?: boolean;
  /** undefined = no sound toggle; the App keys it to `persistent` */
  soundPersistent?: boolean;
}) {
  const tally = runTally(state);
  const period = periodLabel(state.period);
  const snapshotCount = new Set(state.sealed.map((s) => s.period)).size;
  return (
    <main className="page-wide">
      <Letterhead period={state.period} status="IN SESSION" statusGloss="in-session" />
      <hr className="rule-double" />
      <header className="my-6">
        <h1 className="t-headline press m-0">
          {period} run
        </h1>
        <p className="screen-sub" data-testid="screen-sub">
          {SUBTITLES.board}
        </p>
        {/* milestone slot: true counts only */}
        <p role="status" data-testid="run-tally" className="t-micro muted">
          {milestoneLine({ period, sealedCount: tally.sealedCount, totalClients: tally.totalClients })}{" "}
          <strong className="t-figure savings">
            ${tally.foundUsd.toLocaleString("en-US", { maximumFractionDigits: 0 })}/mo found
          </strong>
        </p>
      </header>
      {firstRunPersistent !== undefined && <FirstRunSlip persistent={firstRunPersistent} />}
      {state.clients.length === 0 && (
        <EmptyState
          what="No clients on the docket"
          how="Clients appear here once a usage export is loaded for them — see the README's demo instructions for loading a Microsoft 365 or GitHub Copilot export."
        />
      )}
      <div className="board">
        {COLUMNS.map(({ stage, title }) => (
          <section key={stage} aria-label={title}>
            <h2 className="t-label section-head">
              <span>
                <Gloss term={stage}>{title}</Gloss>
              </span>
              <span className="t-figure muted">
                {state.clients.filter((c) => stageOf(state, c.id) === stage).length}
              </span>
            </h2>
            {state.clients.filter((c) => stageOf(state, c.id) === stage).length === 0 && (
              <p aria-hidden="true" className="column-empty">
                —
              </p>
            )}
            {state.clients
              .filter((c) => stageOf(state, c.id) === stage)
              .map((c) => {
                const sealedSnap = state.sealed.find(
                  (s) => s.clientId === c.id && s.period === state.period,
                );
                return (
                  <button
                    key={c.id}
                    onClick={() => onOpenClient(c.id)}
                    className="btn-bare"
                  >
                    <ClientTile
                      client={{
                        name: c.name,
                        stage,
                        sealedSavingsUsd: sealedSnap?.savingsUsd,
                        casesRemaining: stage === "in-review" ? casesRemaining(c) : undefined,
                        stats: c.seats
                          ? {
                              seats: c.seats.length,
                              reclaimSuggested: c.seats.filter((s) => s.verdict === "reclaim").length,
                              potentialUsd: projectedSavings(c.seats),
                            }
                          : undefined,
                      }}
                    />
                    {/* post-seal exhale — the one wry line near the seal,
                        AFTER the sincere confirm (blueprint §2.1) */}
                    {sealedSnap && (
                      <p className="exhale t-micro muted">
                        ${sealedSnap.savingsUsd.toLocaleString("en-US")} herewith returned to the general fund.
                      </p>
                    )}
                  </button>
                );
              })}
          </section>
        ))}
      </div>
      <footer
        className="slip mt-12 muted"
      >
        <hr className="rule-double" />
        {/* office sound is strictly opt-in (gui-10) */}
        {soundPersistent !== undefined && (
          <p>
            <SoundToggle persistent={soundPersistent} />
          </p>
        )}
        {/* ambient slot: renders the true aggregate of the open period */}
        <p data-testid="ambient-line" className="t-micro">
          {ambientLine({ period, decorativeSeatPct: decorativeSeatPct(state) })}
        </p>
        {/* exhibit slot: the vendor-amnesia jab over real snapshot counts */}
        <p data-testid="exhibit-caption" className="eyebrow">
          {exhibitCaption({ snapshotCount, vendorRetentionDays: 90 })}
        </p>
        {/* QBR entry points — only clients with sealed history qualify */}
        {onOpenQBR &&
          !state.clients.some((c) => state.sealed.some((s) => s.clientId === c.id)) && (
            <p data-testid="qbr-empty" className="t-micro">
              <Gloss term="qbr">QBR packs</Gloss> appear here once a client has a sealed month.
            </p>
          )}
        {onOpenQBR && (
          <p data-testid="qbr-links">
            {state.clients
              .filter((c) => state.sealed.some((s) => s.clientId === c.id))
              .map((c) => (
                <button
                  key={c.id}
                  onClick={() => onOpenQBR(c.id, quarterOf(state.period))}
                  className="mr-2"
                >
                  {c.name} · {quarterOf(state.period)} QBR pack
                </button>
              ))}
          </p>
        )}
      </footer>
    </main>
  );
}

export function periodLabel(period: string): string {
  const [y, m] = period.split("-");
  const names = ["January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"];
  return `${names[Number(m) - 1]} ${y}`;
}
