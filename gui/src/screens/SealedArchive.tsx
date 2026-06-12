import { SUBTITLES } from "../clarity";
import { ReportPreview } from "../components/ReportPreview";
import { SealCrest } from "../components/SealCrest";
import type { SealedSnapshot } from "../store";
import { periodLabel } from "./RunBoard";

/** The archived record (blueprint §3.4): renders the FROZEN snapshot's
 * seats — never the live client — so the archive can't drift from what was
 * sealed. Read-only and voice-free by construction; no edit affordance
 * exists on this screen. */
export function SealedArchive({
  snapshot,
  clientName,
  mspName,
  caveats,
  onBack,
}: {
  snapshot: SealedSnapshot;
  clientName: string;
  mspName: string;
  caveats: readonly string[];
  onBack: () => void;
}) {
  return (
    <main className="page">
      <p>
        <button onClick={onBack}>⟵ back to the run</button>
      </p>
      <p className="screen-sub" data-testid="screen-sub">
        {SUBTITLES.archive}
      </p>
      <p className="eyebrow" data-testid="sealed-at">
        Sealed record · {periodLabel(snapshot.period)} · sealed{" "}
        {new Date(snapshot.sealedAt).toLocaleDateString("en-US", {
          year: "numeric",
          month: "long",
          day: "numeric",
        })}
        {" — "}this report is part of the permanent record and cannot change.
      </p>
      <div className="pos-rel">
        <ReportPreview
          seats={snapshot.seats}
          mspName={mspName}
          clientName={clientName}
          caveats={caveats}
        />
        {/* the emboss — pressed over the document's corner, decorative */}
        <div
          aria-hidden="true"
          className="archive-crest"
        >
          <SealCrest period={snapshot.period} />
        </div>
      </div>
    </main>
  );
}
