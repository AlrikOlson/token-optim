import { describe, expect, it } from "vitest";
import {
  ambientLine,
  evidenceLine,
  exhibitCaption,
  milestoneLine,
  plainEvidence,
} from "./voice";

describe("Committee voice engine", () => {
  it("is deterministic: same payload, same line, every time", () => {
    const p = { kind: "idle", user: "m.ruiz", idleDays: 92, seatCostUsd: 30 } as const;
    expect(evidenceLine(p)).toBe(evidenceLine(p));
  });

  it("rotates across cases (different payloads can draw different templates)", () => {
    const lines = new Set(
      ["a", "b", "c", "d", "e", "f", "g", "h"].map((u) =>
        evidenceLine({ kind: "never-used", user: u, seatCostUsd: 30 }),
      ),
    );
    expect(lines.size).toBeGreaterThan(1);
  });

  it("every line carries its true payload values (humor is load-bearing)", () => {
    const idle = evidenceLine({ kind: "idle", user: "x", idleDays: 64, seatCostUsd: 30 });
    expect(idle).toContain("64");
    expect(idle).toContain("$30");
    const never = evidenceLine({ kind: "never-used", user: "y", seatCostUsd: 19 });
    expect(never).toContain("$19");
    const noRec = evidenceLine({ kind: "no-record", user: "z", retentionDays: 90 });
    expect(noRec).toContain("90");
  });

  it("plain fallback states the same facts without the register", () => {
    const p = { kind: "idle", user: "x", idleDays: 64, seatCostUsd: 30 } as const;
    const plain = plainEvidence(p);
    expect(plain).toContain("64");
    expect(plain).not.toContain("NOTICE");
    expect(plain).not.toContain("committee");
  });

  it("comprehensibility rule (gui-14): EVERY rotation template still states the plain fact", () => {
    // a reader who misses the joke must still get the money and the days —
    // sweep many seeds so every template in the rotation is exercised
    const users = Array.from({ length: 24 }, (_, i) => `user${i}`);
    for (const u of users) {
      expect(evidenceLine({ kind: "never-used", user: u, seatCostUsd: 30 })).toContain("$30");
      const idle = evidenceLine({ kind: "idle", user: u, idleDays: 41, seatCostUsd: 19 });
      expect(idle).toContain("41");
      expect(idle).toContain("$19");
      expect(evidenceLine({ kind: "no-record", user: u, retentionDays: 90 })).toContain("90");
    }
  });

  it("milestone distinguishes cleared from in-session, with true counts", () => {
    expect(milestoneLine({ period: "June 2026", sealedCount: 12, totalClients: 12 }))
      .toContain("docket cleared");
    const partial = milestoneLine({ period: "June 2026", sealedCount: 9, totalClients: 12 });
    expect(partial).toContain("9 of 12");
    expect(partial).not.toContain("cleared");
  });

  it("ambient line renders the true aggregate", () => {
    expect(ambientLine({ period: "Jun 2026", decorativeSeatPct: 14 })).toContain("14%");
  });

  it("exhibit caption spans A–N by snapshot count and names retention", () => {
    expect(exhibitCaption({ snapshotCount: 4, vendorRetentionDays: 90 }))
      .toContain("EXHIBIT A–D");
    expect(exhibitCaption({ snapshotCount: 1, vendorRetentionDays: 90 }))
      .toContain("EXHIBIT A:");
  });
});
