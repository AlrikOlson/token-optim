/** Client-side app store mirroring snapshots.py semantics:
 *  - sealed snapshots are append-only (no reducer action mutates them);
 *  - sealing is REFUSED while cases remain unheard (the invariant lives in
 *    the state machine, not the button);
 *  - tile stage is derived, never set by hand.
 * Backend wiring to the Python SnapshotStore is pv-5 scope. */

import type { Seat, Verdict } from "./domain";
import { projectedSavings } from "./domain";
import { suggestedSeat, type SeatActivity } from "./rules";

export interface SealedSnapshot {
  clientId: string;
  period: string;
  seats: readonly Seat[];
  savingsUsd: number;
  sealedAt: string;
}

export interface ClientRun {
  id: string;
  name: string;
  /** null = no export ingested yet for the period (awaiting data). */
  seats: readonly Seat[] | null;
  /** Users whose case has been heard (ratified or overridden). */
  heard: readonly string[];
}

export interface AppState {
  period: string; // "2026-06"
  clients: readonly ClientRun[];
  sealed: readonly SealedSnapshot[]; // across all periods — the moat
}

export type Stage = "awaiting-data" | "verdicts-in" | "in-review" | "sealed";

export function stageOf(state: AppState, clientId: string): Stage {
  if (state.sealed.some((s) => s.clientId === clientId && s.period === state.period)) {
    return "sealed";
  }
  const c = state.clients.find((c) => c.id === clientId);
  if (!c || c.seats === null) return "awaiting-data";
  return c.heard.length === 0 ? "verdicts-in" : "in-review";
}

export function casesRemaining(c: ClientRun): number {
  return (c.seats?.length ?? 0) - c.heard.length;
}

export function runTally(state: AppState): { sealedCount: number; totalClients: number; foundUsd: number } {
  const sealedNow = state.sealed.filter((s) => s.period === state.period);
  return {
    sealedCount: sealedNow.length,
    totalClients: state.clients.length,
    foundUsd: sealedNow.reduce((t, s) => t + s.savingsUsd, 0),
  };
}

/** True aggregate behind the ambient FINDINGS line. */
export function decorativeSeatPct(state: AppState): number {
  const seats = state.clients.flatMap((c) => c.seats ?? []);
  if (seats.length === 0) return 0;
  const decorative = seats.filter((s) => s.verdict === "reclaim").length;
  return Math.round((decorative / seats.length) * 100);
}

// ----------------------------------------------------------- persistence

/** Versioned key: a schema change bumps the version and reseeds rather
 * than crashing on stale data. */
export const STORAGE_KEY = "token-optim/state/v1";

export function loadPersisted(): AppState | null {
  try {
    const raw = globalThis.localStorage?.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as AppState;
    // minimal shape check — corrupt data falls back to seed
    if (!parsed.period || !Array.isArray(parsed.clients) || !Array.isArray(parsed.sealed)) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function persist(state: AppState): void {
  try {
    globalThis.localStorage?.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // storage full/unavailable: the app keeps working, state is session-only
  }
}

/** "2026-05" -> "Q2 2026". */
export function quarterOf(period: string): string {
  const [y, m] = period.split("-").map(Number);
  return `Q${Math.ceil(m / 3)} ${y}`;
}

/** QBR assembly (blueprint §3.5): reads state.sealed and ONLY state.sealed,
 * so drafts are invisible to the QBR by construction — the QBRPack
 * component then independently throws if anything unsealed slips through. */
export function qbrSnapshots(
  state: AppState,
  clientId: string,
  quarter: string,
): { period: string; savingsUsd: number; sealed: true }[] {
  return state.sealed
    .filter((s) => s.clientId === clientId && quarterOf(s.period) === quarter)
    .sort((a, b) => a.period.localeCompare(b.period))
    .map((s) => ({ period: s.period, savingsUsd: s.savingsUsd, sealed: true }));
}

export type Action =
  | { type: "hear"; clientId: string; user: string; verdict: Verdict }
  | { type: "accept-all-suggested"; clientId: string }
  | { type: "seal"; clientId: string; sealedAt: string };

export function reduce(state: AppState, action: Action): AppState {
  switch (action.type) {
    case "hear": {
      return {
        ...state,
        clients: state.clients.map((c) => {
          if (c.id !== action.clientId || c.seats === null) return c;
          return {
            ...c,
            seats: c.seats.map((s) =>
              s.user === action.user && s.verdict !== action.verdict
                ? {
                    ...s,
                    verdict: action.verdict,
                    monthlySavingUsd:
                      action.verdict === "reclaim" ? Math.max(s.monthlySavingUsd, seatCostOf(s)) : 0,
                    reason: `${s.reason} — reviewer override`,
                  }
                : s,
            ),
            heard: c.heard.includes(action.user) ? c.heard : [...c.heard, action.user],
          };
        }),
      };
    }
    case "accept-all-suggested": {
      return {
        ...state,
        clients: state.clients.map((c) =>
          c.id === action.clientId && c.seats !== null
            ? { ...c, heard: c.seats.map((s) => s.user) }
            : c,
        ),
      };
    }
    case "seal": {
      const c = state.clients.find((c) => c.id === action.clientId);
      if (!c || c.seats === null) return state;
      // Structural invariant: sealing is refused while cases remain.
      if (casesRemaining(c) > 0) return state;
      if (stageOf(state, c.id) === "sealed") return state; // sealed is forever
      const snapshot: SealedSnapshot = {
        clientId: c.id,
        period: state.period,
        seats: c.seats,
        savingsUsd: projectedSavings(c.seats),
        sealedAt: action.sealedAt,
      };
      return { ...state, sealed: [...state.sealed, snapshot] };
    }
  }
}

/** Seat-cost lookup for overrides: the original suggestion carries the cost
 * for reclaim verdicts; for keep→reclaim overrides we use the product list
 * price (mirrors snapshots.PRODUCT_SEAT_COST_DEFAULTS). */
const SEAT_COSTS = { m365: 30, github: 19 } as const;
function seatCostOf(s: Seat): number {
  return SEAT_COSTS[s.product];
}

// ------------------------------------------------------------- seed data

function org(
  id: string,
  name: string,
  activities: SeatActivity[] | null,
): ClientRun {
  return {
    id,
    name,
    seats: activities?.map((a) => suggestedSeat(a, SEAT_COSTS[a.product])) ?? null,
    heard: [],
  };
}

const m = (domain: string) =>
  (user: string, days: number | null, apps?: number): SeatActivity => ({
    user: `${user}@${domain}`,
    product: "m365",
    daysSinceLastActivity: days,
    activeApps: apps,
    appsTracked: apps !== undefined,
  });

const g = (user: string, days: number | null): SeatActivity => ({
  user,
  product: "github",
  daysSinceLastActivity: days,
});

export function seedState(period = "2026-06"): AppState {
  const fab = m("fabrikam-demo.com");
  const con = m("contoso-demo.com");
  return {
    period,
    clients: [
      org("fabrikam", "Fabrikam Manufacturing", [
        fab("maria.chen", 2, 3), fab("dev.patel", 3, 3), fab("sofia.reyes", 4, 2),
        fab("raj.kumar", 22, 1), fab("emily.watts", 25, 1),
        fab("mark.olsen", 92), fab("tina.gomez", 70),
        fab("bob.tanner", null), fab("sue.ellis", null),
        g("dev-eng-01", 5), g("dev-eng-04", 80), g("dev-eng-07", null),
      ]),
      org("contoso", "Contoso Ltd", [
        con("a.chen", 1, 3), con("j.smith", 30, 1), con("m.ruiz", null),
        con("k.patel", 64), con("p.singh", 20, 1), con("d.okafor", 41, 2),
      ]),
      org("northwind", "Northwind Traders", null), // awaiting data
    ],
    sealed: [
      {
        clientId: "fabrikam",
        period: "2026-05",
        seats: [],
        savingsUsd: 210,
        sealedAt: "2026-05-30T17:00:00Z",
      },
      {
        clientId: "contoso",
        period: "2026-05",
        seats: [],
        savingsUsd: 150,
        sealedAt: "2026-05-29T09:00:00Z",
      },
    ],
  };
}
