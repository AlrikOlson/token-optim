import { describe, expect, it } from "vitest";
import { NO_RECORD_PHRASE, RULES_SPEC, suggestVerdict } from "./rules";

/* Golden vectors mirrored verbatim in test_demo.py (RULE_GOLDEN) — the two
 * interpreters of rules-spec.json must decide identically (gui-1b). */
const GOLDEN: Array<[number | null, number, boolean, string]> = [
  [null, 0, false, "reclaim"],
  [90, 0, false, "reclaim"],
  [46, 0, false, "reclaim"],
  [45, 0, false, "review"], // boundary: not > 45
  [15, 0, false, "review"],
  [14, 1, true, "review"], // single-app use, tracked
  [14, 2, true, "keep"],
  [14, 0, false, "keep"], // boundary: not > 14, untracked
  [0, 3, true, "keep"],
];

describe("rules-spec convergence", () => {
  it("decides the golden vectors exactly like advisory.py", () => {
    for (const [days, apps, tracked, expected] of GOLDEN) {
      const { verdict } = suggestVerdict({
        user: "probe@x.com",
        product: "m365",
        daysSinceLastActivity: days,
        activeApps: apps,
        appsTracked: tracked,
      });
      expect(verdict, `days=${days} apps=${apps} tracked=${tracked}`).toBe(expected);
    }
  });

  it("consumes the generated spec, not hand-kept literals", () => {
    expect(RULES_SPEC.version).toBe(1);
    expect(RULES_SPEC.thresholds.reclaim_after_days).toBe(45);
    expect(RULES_SPEC.thresholds.review_after_days).toBe(14);
    expect(RULES_SPEC.thresholds.single_app_max).toBe(1);
    expect(RULES_SPEC.stated.map((s) => s.verdict)).toEqual(["keep", "review", "reclaim"]);
  });

  it("keeps the GUI's no-record phrasing (surface semantics, not drift)", () => {
    const { reason } = suggestVerdict({
      user: "probe@x.com",
      product: "m365",
      daysSinceLastActivity: null,
    });
    expect(reason).toBe(NO_RECORD_PHRASE);
  });
});
