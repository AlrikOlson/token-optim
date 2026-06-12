import { SUBTITLES } from "../clarity";
import { QBRPack } from "../components/QBRPack";
import type { AppState } from "../store";
import { qbrSnapshots } from "../store";

/** Blueprint §3.5 — the quarterly deliverable view. Client-ready register:
 * this screen imports nothing from voice.ts. */
export function QBRView({
  state,
  clientId,
  quarter,
  onBack,
}: {
  state: AppState;
  clientId: string;
  quarter: string;
  onBack: () => void;
}) {
  const client = state.clients.find((c) => c.id === clientId);
  const snapshots = qbrSnapshots(state, clientId, quarter);
  if (!client) return null;
  return (
    <main className="page">
      <p>
        <button onClick={onBack}>⟵ back to the run</button>
      </p>
      <p className="screen-sub" data-testid="screen-sub">
        {SUBTITLES.qbr}
      </p>
      {snapshots.length > 0 ? (
        <QBRPack clientName={client.name} quarter={quarter} snapshots={snapshots} />
      ) : (
        <p role="status">
          No sealed months for {client.name} in {quarter} yet — the QBR pack
          assembles only from sealed reports.
        </p>
      )}
    </main>
  );
}
