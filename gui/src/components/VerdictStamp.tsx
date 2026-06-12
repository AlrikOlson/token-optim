import type { Verdict } from "../domain";
import { erosionVariant, stampTilt } from "../hash";
import { EROSION_VARIANTS } from "./InkBleedDefs";

const VERDICT_VAR: Record<Verdict, string> = {
  keep: "var(--verdict-keep)",
  review: "var(--verdict-review)",
  reclaim: "var(--verdict-reclaim)",
};

/** A rubber stamp (design law: all three verdicts are stamped). Tilt is
 * deterministic per user — the same case always reads the same on every
 * surface (stampTilt is mirrored byte-for-byte in demo.py) — and each
 * impression wears its own seeded erosion filter from InkBleedDefs. */
export function VerdictStamp({ verdict, seed }: { verdict: Verdict; seed: string }) {
  const tilt = stampTilt(seed); // -2°..+2°
  const erosion = erosionVariant(seed, EROSION_VARIANTS);
  return (
    <span
      className="stamp"
      data-verdict={verdict}
      /* inline-ok(data): verdict ink + deterministic per-seat tilt + pad wear */
      style={{
        color: VERDICT_VAR[verdict],
        ["--stamp-tilt" as string]: `${tilt}deg`,
        filter: `url(#ink-bleed-${erosion})`,
      }}
    >
      {verdict}
    </span>
  );
}
