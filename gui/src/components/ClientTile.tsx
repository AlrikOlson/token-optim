import type { ClientStage, ClientTileData } from "../domain";
import { stableHash } from "../hash";
import { vtName } from "../vt";

const STAGE_LABEL: Record<ClientStage, string> = {
  "awaiting-data": "awaiting data",
  "verdicts-in": "verdicts in",
  "in-review": "in review",
  sealed: "sealed & delivered",
};

const STAGE_COLOR: Record<ClientStage, string> = {
  "awaiting-data": "var(--ink-faint)",
  "verdicts-in": "var(--accent)",
  "in-review": "var(--verdict-review)",
  sealed: "var(--verdict-keep)",
};

/** Run Board tile (blueprint §3.1) — an index card LYING on the docket
 * sheet, carrying true figures. System classes throughout; inline styles
 * carry only data-driven values (tilt, stage color, transition name). */
export function ClientTile({ client }: { client: ClientTileData }) {
  const tilt = ((stableHash(`${client.name}|lie`) % 9) - 4) * 0.2; // ±0.8°
  return (
    <div
      className="client-tile sheet lies stack-2"
      data-stage={client.stage}
      /* inline-ok(data): stage color, per-instance tilt, vt name */
      style={{
        borderTop: `4px solid ${STAGE_COLOR[client.stage]}`,
        ["--lie-tilt" as string]: `${tilt}deg`,
        viewTransitionName: vtName("tile", client.name),
      }}
    >
      <strong className="t-title press block">
        {client.name}
      </strong>
      {/* inline-ok(data): stage color */}
      <div className="t-micro strong" style={{ color: STAGE_COLOR[client.stage] }}>
        {STAGE_LABEL[client.stage]}
        {client.stage === "in-review" && client.casesRemaining !== undefined && (
          <> · {client.casesRemaining} left</>
        )}
      </div>
      {client.stage === "sealed" && client.sealedSavingsUsd !== undefined ? (
        <div className="t-figure-lg savings press" data-testid="tile-savings">
          ${client.sealedSavingsUsd.toLocaleString("en-US", { maximumFractionDigits: 0 })} ✓
        </div>
      ) : client.stats ? (
        <div
          className="t-micro muted tile-stats"
          data-testid="tile-stats"
        >
          <span>{client.stats.seats} seats</span>
          <span className="reclaim-ink">
            {client.stats.reclaimSuggested} reclaim
          </span>
          <span className="savings">
            ${client.stats.potentialUsd.toLocaleString("en-US", { maximumFractionDigits: 0 })}/mo
          </span>
        </div>
      ) : (
        <div className="t-micro faint">no export on file</div>
      )}
    </div>
  );
}
