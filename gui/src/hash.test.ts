import { describe, expect, it } from "vitest";
import { erosionVariant, stableHash, stampTilt } from "./hash";

/* Golden vectors shared verbatim with test_demo.py — if either side drifts
 * from FNV-1a-over-UTF-16(`user|stamp`), the same seat would stamp at a
 * different angle on the report than in the GUI (gui-11 unification). */
const GOLDEN: Array<[string, number, number]> = [
  ["alice@fabrikam.com", 794089938, -0.5],
  ["bob.briggs@initech.com", 39313206, -2],
  ["Žofie Nováková", 787488327, -2],
  ["龍太郎", 2516235835, 0],
];

describe("stableHash / stampTilt cross-surface parity", () => {
  it("matches the golden vectors mirrored in test_demo.py", () => {
    for (const [user, hash, tilt] of GOLDEN) {
      expect(stableHash(`${user}|stamp`)).toBe(hash);
      expect(stampTilt(user)).toBe(tilt);
    }
  });

  it("tilts stay in the stamp's physical range, half-degree steps", () => {
    for (let i = 0; i < 200; i++) {
      const t = stampTilt(`user-${i}@example.com`);
      expect(t).toBeGreaterThanOrEqual(-2);
      expect(t).toBeLessThanOrEqual(2);
      expect(Number.isInteger(t * 2)).toBe(true); // half-degree steps
    }
  });
});

describe("erosionVariant", () => {
  it("is deterministic and in range", () => {
    for (let i = 0; i < 100; i++) {
      const v = erosionVariant(`seat-${i}`, 8);
      expect(v).toBe(erosionVariant(`seat-${i}`, 8));
      expect(v).toBeGreaterThanOrEqual(0);
      expect(v).toBeLessThan(8);
    }
  });

  it("actually varies across seats (worn pads differ)", () => {
    const seen = new Set(
      Array.from({ length: 64 }, (_, i) => erosionVariant(`seat-${i}`, 8)),
    );
    expect(seen.size).toBeGreaterThan(1);
  });
});
