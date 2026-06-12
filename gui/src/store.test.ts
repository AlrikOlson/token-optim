import { describe, expect, it } from "vitest";
import { projectedSavings } from "./domain";
import { NO_RECORD_PHRASE, suggestVerdict } from "./rules";
import {
  STORAGE_KEY,
  casesRemaining,
  decorativeSeatPct,
  loadPersisted,
  persist,
  qbrSnapshots,
  quarterOf,
  reduce,
  runTally,
  seedState,
  stageOf,
} from "./store";

const sealAll = (state = seedState(), clientId = "contoso") => {
  let s = reduce(state, { type: "accept-all-suggested", clientId });
  s = reduce(s, { type: "seal", clientId, sealedAt: "2026-06-30T00:00:00Z" });
  return s;
};

describe("rules mirror advisory.py", () => {
  it("nil activity phrases the vendor-retention truth", () => {
    expect(suggestVerdict({ user: "x", product: "github", daysSinceLastActivity: null }).reason)
      .toBe(NO_RECORD_PHRASE);
  });
  it("stated thresholds match (45/14 days, single-app review)", () => {
    expect(suggestVerdict({ user: "x", product: "m365", daysSinceLastActivity: 46 }).verdict).toBe("reclaim");
    expect(suggestVerdict({ user: "x", product: "m365", daysSinceLastActivity: 15 }).verdict).toBe("review");
    expect(suggestVerdict({ user: "x", product: "m365", daysSinceLastActivity: 5, activeApps: 1, appsTracked: true }).verdict).toBe("review");
    expect(suggestVerdict({ user: "x", product: "m365", daysSinceLastActivity: 5, activeApps: 3, appsTracked: true }).verdict).toBe("keep");
  });
});

describe("store — structural invariants", () => {
  it("seal is REFUSED while cases remain", () => {
    const s0 = seedState();
    const s1 = reduce(s0, { type: "seal", clientId: "contoso", sealedAt: "t" });
    expect(s1).toBe(s0); // unchanged — the reducer refused
    expect(stageOf(s1, "contoso")).not.toBe("sealed");
  });

  it("seal works once all cases are heard, and is then forever", () => {
    const s = sealAll();
    expect(stageOf(s, "contoso")).toBe("sealed");
    const sealedCount = s.sealed.length;
    // re-seal attempts add nothing
    const s2 = reduce(s, { type: "seal", clientId: "contoso", sealedAt: "t2" });
    expect(s2.sealed.length).toBe(sealedCount);
    // hearing a sealed client's seat doesn't resurrect the draft stage
    expect(stageOf(reduce(s, { type: "hear", clientId: "contoso", user: "m.ruiz@contoso-demo.com", verdict: "keep" }), "contoso")).toBe("sealed");
  });

  it("sealed snapshot carries the exact projectedSavings of its seats", () => {
    const s = sealAll();
    const snap = s.sealed.find((x) => x.clientId === "contoso" && x.period === "2026-06")!;
    expect(snap.savingsUsd).toBe(projectedSavings(snap.seats));
  });

  it("override recomputes savings with per-product cost", () => {
    const s0 = seedState();
    // a.chen is a keep (m365); override to reclaim => $30
    const s1 = reduce(s0, { type: "hear", clientId: "contoso", user: "a.chen@contoso-demo.com", verdict: "reclaim" });
    const seat = s1.clients.find((c) => c.id === "contoso")!.seats!
      .find((x) => x.user === "a.chen@contoso-demo.com")!;
    expect(seat.monthlySavingUsd).toBe(30);
    expect(seat.reason).toContain("reviewer override");
  });

  it("stage derivation: awaiting-data -> verdicts-in -> in-review -> sealed", () => {
    const s0 = seedState();
    expect(stageOf(s0, "northwind")).toBe("awaiting-data");
    expect(stageOf(s0, "contoso")).toBe("verdicts-in");
    const s1 = reduce(s0, { type: "hear", clientId: "contoso", user: "m.ruiz@contoso-demo.com", verdict: "reclaim" });
    expect(stageOf(s1, "contoso")).toBe("in-review");
    expect(casesRemaining(s1.clients.find((c) => c.id === "contoso")!)).toBe(5);
  });

  it("run tally counts only this period's sealed snapshots", () => {
    const s0 = seedState(); // two sealed snapshots exist, both 2026-05
    expect(runTally(s0)).toEqual({ sealedCount: 0, totalClients: 3, foundUsd: 0 });
    const s1 = sealAll(s0);
    expect(runTally(s1).sealedCount).toBe(1);
    expect(runTally(s1).foundUsd).toBeGreaterThan(0);
  });

  it("quarterOf groups periods correctly", () => {
    expect(quarterOf("2026-01")).toBe("Q1 2026");
    expect(quarterOf("2026-06")).toBe("Q2 2026");
    expect(quarterOf("2026-12")).toBe("Q4 2026");
  });

  it("qbrSnapshots assembles ONLY sealed snapshots, chronologically", () => {
    const s = sealAll(); // contoso has 2026-05 (seeded) + 2026-06 (sealed now)
    const q2 = qbrSnapshots(s, "contoso", "Q2 2026");
    expect(q2.map((x) => x.period)).toEqual(["2026-05", "2026-06"]);
    expect(q2.every((x) => x.sealed)).toBe(true);
    // fabrikam's June is an unsealed draft — invisible to the QBR
    const fab = qbrSnapshots(s, "fabrikam", "Q2 2026");
    expect(fab.map((x) => x.period)).toEqual(["2026-05"]);
  });

  it("ambient aggregate is a true percentage of reclaim seats", () => {
    const s = seedState();
    const seats = s.clients.flatMap((c) => c.seats ?? []);
    const expected = Math.round(
      (seats.filter((x) => x.verdict === "reclaim").length / seats.length) * 100,
    );
    expect(decorativeSeatPct(s)).toBe(expected);
  });
});

describe("persistence — the moat survives reload", () => {
  it("round-trips full state including sealed snapshots and heard progress", () => {
    localStorage.clear();
    const sealed = sealAll();
    persist(sealed);
    const back = loadPersisted()!;
    expect(back).toEqual(sealed);
    expect(back.sealed.some((s) => s.period === "2026-06")).toBe(true);
  });

  it("missing or corrupt data falls back to null (seed path)", () => {
    localStorage.clear();
    expect(loadPersisted()).toBeNull();
    localStorage.setItem(STORAGE_KEY, "{not json");
    expect(loadPersisted()).toBeNull();
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ wrong: "shape" }));
    expect(loadPersisted()).toBeNull();
  });
});
