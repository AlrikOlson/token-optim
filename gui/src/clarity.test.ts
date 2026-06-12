import { describe, expect, it } from "vitest";
import { APP_PURPOSE, GLOSSARY, SUBTITLES } from "./clarity";

/** The clarity layer's register rules, mechanically enforced (gui-14):
 * plain language only — the Memo voice must never leak into the layer
 * whose whole job is to explain the Memo voice. */
describe("clarity layer register", () => {
  const allCopy = [APP_PURPOSE, ...Object.values(SUBTITLES), ...Object.values(GLOSSARY)];

  it("never speaks Committee (no parody markers, no shouting)", () => {
    for (const line of allCopy) {
      expect(line).not.toMatch(/NOTICE:|committee|herewith|hereinafter/i);
      expect(line).not.toContain("!");
    }
  });

  it("every screen has a subtitle and every subtitle is one or two short sentences", () => {
    for (const [screen, sub] of Object.entries(SUBTITLES)) {
      expect(sub.length, screen).toBeGreaterThan(20);
      expect(sub.length, screen).toBeLessThan(160);
    }
  });

  it("glosses are self-contained: no gloss leans on another Memo term in caps", () => {
    // a gloss that explains jargon WITH jargon fails its one job
    for (const [key, gloss] of Object.entries(GLOSSARY)) {
      expect(gloss, key).not.toMatch(/\b(DOCKET|VERDICT|HEARING|EXHIBIT|QBR PACK)\b/);
    }
  });

  it("the purpose statement names both products and the core loop", () => {
    expect(APP_PURPOSE).toContain("Microsoft 365");
    expect(APP_PURPOSE).toContain("GitHub Copilot");
    expect(APP_PURPOSE).toMatch(/seal/i);
  });
});
