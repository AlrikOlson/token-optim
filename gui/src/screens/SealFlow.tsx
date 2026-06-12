import { SUBTITLES } from "../clarity";
import { ReportPreview } from "../components/ReportPreview";
import type { ClientRun } from "../store";

/** Blueprint §3.3 — the sincere Seal. This screen imports nothing from
 * voice.ts: real money, a locked period, stated caveats. The one wry line
 * (the exhale) lives on the Run Board, after this confirm. */
export function SealFlow({
  client,
  mspName,
  caveats,
  onConfirm,
  onBack,
}: {
  client: ClientRun;
  mspName: string;
  caveats: readonly string[];
  onConfirm: () => void;
  onBack: () => void;
}) {
  const seats = client.seats ?? [];
  return (
    <main className="page">
      <h1 className="t-title press">Seal {client.name}</h1>
      <p className="screen-sub" data-testid="screen-sub">
        {SUBTITLES.seal} The report below is what the client receives; it
        cannot be edited afterward.
      </p>
      <ReportPreview
        seats={seats}
        mspName={mspName}
        clientName={client.name}
        caveats={caveats}
      />
      <p className="mt-4">
        <button onClick={onBack} className="mr-2">
          Back
        </button>
        <button
          onClick={onConfirm}
          data-testid="seal-confirm"
          className="btn-primary"
        >
          Seal &amp; deliver ⟶
        </button>
      </p>
    </main>
  );
}
