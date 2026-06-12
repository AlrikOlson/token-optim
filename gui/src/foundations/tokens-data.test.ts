import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { groupOf, parseTokens } from "./tokens-data";

// vitest's jsdom project intercepts .css imports (even ?raw), so the unit
// suite reads the stylesheet from disk and exercises the pure parser. The
// browser-mode Foundations stories cover the ?raw wiring itself.
// (cwd is the vitest root = gui/; import.meta.url is http: under jsdom.)
const css = readFileSync(join(process.cwd(), "src/tokens.css"), "utf8");
const tokens = parseTokens(css);

describe("tokens-data (the Foundations parser)", () => {
  it("parses a substantial token set from tokens.css", () => {
    expect(tokens.length).toBeGreaterThanOrEqual(35);
  });

  it("captures dark-theme overrides where declared", () => {
    const ink = tokens.find((t) => t.name === "--ink");
    expect(ink?.light).toBe("#211d16");
    expect(ink?.dark).toBe("#cfe3cd");
    // spacing has no microfiche override — geometry is theme-invariant
    const space = tokens.find((t) => t.name === "--space-4");
    expect(space?.dark).toBeUndefined();
  });

  it("assigns every token to a named group — nothing falls to 'other'", () => {
    // 'other' existing as a catch-all is fine; a token actually LANDING there
    // means the catalog has an unfiled specimen — file it before shipping.
    const strays = tokens.filter((t) => groupOf(t.name) === "other");
    expect(strays.map((t) => t.name)).toEqual([]);
  });

  it("upholds the shape law: every radius token is 0px", () => {
    for (const t of tokens.filter((t) => t.name.startsWith("--radius"))) {
      expect(t.light).toBe("0px");
    }
  });

  it("multi-line values (data URLs, linear()) survive the parser intact", () => {
    const spring = tokens.find((t) => t.name === "--ease-spring");
    expect(spring?.light).toContain("linear(");
    const grain = tokens.find((t) => t.name === "--grain");
    expect(grain?.light).toContain("data:image/svg+xml");
  });
});
