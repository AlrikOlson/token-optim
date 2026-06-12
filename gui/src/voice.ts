/** The Committee voice engine (UX-BLUEPRINT v5 §2.1).
 *
 * The app speaks in bureaucratic parody ONLY through the four slots below,
 * and every line is built from a typed data payload — there is no free-text
 * entry point, so a wry line literally cannot render without a backing true
 * value. The client-facing report layer must never import this module.
 *
 * Rotation is deterministic (FNV-1a over the payload), never Math.random:
 * the same case reads the same on every render, and tests can pin lines.
 */

// ---------------------------------------------------------------- payloads

export type EvidencePayload =
  | { kind: "never-used"; user: string; seatCostUsd: number }
  | { kind: "idle"; user: string; idleDays: number; seatCostUsd: number }
  | { kind: "no-record"; user: string; retentionDays: number };

export interface MilestonePayload {
  period: string; // "June 2026"
  sealedCount: number;
  totalClients: number;
}

export interface AmbientPayload {
  period: string;
  decorativeSeatPct: number; // true aggregate: reclaim+never seats / total
}

export interface ExhibitPayload {
  snapshotCount: number;
  vendorRetentionDays: number;
}

// ------------------------------------------------------------- determinism

import { stableHash } from "./hash";

function pick<T>(templates: readonly T[], seed: string): T {
  return templates[stableHash(seed) % templates.length];
}

const usd = (n: number) => `$${n.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;

// ------------------------------------------------------------------ slots

/** Slot 1 — evidence phrasing (VerdictRow / the stand). Reclaim-grade only;
 * keep/review evidence stays plain (register restraint, blueprint §6.5). */
export function evidenceLine(p: EvidencePayload): string {
  switch (p.kind) {
    case "never-used":
      return pick(
        [
          `NOTICE: this seat has fulfilled its contractual obligation to exist. Usage was at no point part of the arrangement. (${usd(p.seatCostUsd)}/mo)`,
          `NOTICE: no recorded use. The seat remains, as billed, full of potential. (${usd(p.seatCostUsd)}/mo)`,
        ],
        `${p.user}|never`,
      );
    case "idle": {
      const d = `${p.idleDays} day${p.idleDays === 1 ? "" : "s"}`;
      return pick(
        [
          `NOTICE: ${d} without incident. The license billed on time regardless. (${usd(p.seatCostUsd)}/mo)`,
          `FINDINGS: idle ${d}. The committee observes the seat is resting. (${usd(p.seatCostUsd)}/mo)`,
        ],
        `${p.user}|idle${p.idleDays}`,
      );
    }
    case "no-record":
      return `NOTICE: no activity on record — the vendor retains ${p.retentionDays} days and has elected to remember nothing.`;
  }
}

/** Plain fallback for the same payloads (high row counts, reduced register). */
export function plainEvidence(p: EvidencePayload): string {
  switch (p.kind) {
    case "never-used":
      return `never used Copilot (${usd(p.seatCostUsd)}/mo)`;
    case "idle":
      return `inactive ${p.idleDays} days (${usd(p.seatCostUsd)}/mo)`;
    case "no-record":
      return `no activity on record (vendor retains ${p.retentionDays} days)`;
  }
}

/** Slot 2 — milestones & empty states (Run Board). */
export function milestoneLine(p: MilestonePayload): string {
  if (p.sealedCount === p.totalClients) {
    return `The committee finds the ${p.period} docket cleared — ${p.totalClients} of ${p.totalClients} sealed. It thanks itself.`;
  }
  return `${p.sealedCount} of ${p.totalClients} sealed. The ${p.period} docket remains in session.`;
}

/** Slot 3 — the one ambient commentary line (Run Board footer). */
export function ambientLine(p: AmbientPayload): string {
  return `FINDINGS: ${p.decorativeSeatPct}% of audited seats are decorative this period (${p.period}).`;
}

/** Slot 4 — the vendor-amnesia jab (history strip caption). */
export function exhibitCaption(p: ExhibitPayload): string {
  const exhibits = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  const span =
    p.snapshotCount <= 1
      ? "EXHIBIT A"
      : `EXHIBIT A–${exhibits[Math.min(p.snapshotCount, 26) - 1]}`;
  return `${span}: ${p.snapshotCount} month${p.snapshotCount === 1 ? "" : "s"} of records the vendor declined to keep (retention: ${p.vendorRetentionDays} days).`;
}
