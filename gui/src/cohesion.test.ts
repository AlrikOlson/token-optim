/** THE COHESION GATE (gui-13).
 *
 * tokens.css is the only place static styling may live. An inline
 * `style={{...}}` in app code is allowed ONLY for data-driven values —
 * per-instance tilt, stage/verdict/brand colors, view-transition names —
 * and must carry an `inline-ok(<reason>)` comment on the line itself or
 * within the three lines above it.
 *
 * Stories, tests, and the Foundations catalog are exempt: specimens
 * legitimately set one-off layout to frame what they exhibit.
 *
 * If this test fails, either move the styling into tokens.css (the system
 * layer) or, if the value is genuinely data, tag it with its justification.
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const SRC = join(process.cwd(), "src");

function tsxFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) {
      return name === "foundations" ? [] : tsxFiles(p);
    }
    if (!p.endsWith(".tsx")) return [];
    if (/\.(stories|test)\.tsx$/.test(p)) return [];
    return [p];
  });
}

describe("cohesion gate — inline styles are data-driven or they don't exist", () => {
  it("every style={{ in app code carries an inline-ok justification", () => {
    const violations: string[] = [];
    for (const file of tsxFiles(SRC)) {
      const lines = readFileSync(file, "utf8").split("\n");
      lines.forEach((line, i) => {
        if (!line.includes("style={{")) return;
        const window = lines.slice(Math.max(0, i - 3), i + 1).join("\n");
        if (!window.includes("inline-ok(")) {
          violations.push(`${file.replace(SRC, "src")}:${i + 1}: ${line.trim()}`);
        }
      });
    }
    // Move it into tokens.css, or tag it: /* inline-ok(data): <why> */
    expect(violations).toEqual([]);
  });

  it("app code never references undeclared tokens (the --rule-line class of bug)", () => {
    const css = readFileSync(join(SRC, "tokens.css"), "utf8");
    const declared = new Set([...css.matchAll(/(--[\w-]+)\s*:/g)].map((m) => m[1]));
    const violations: string[] = [];
    for (const file of tsxFiles(SRC)) {
      const text = readFileSync(file, "utf8");
      for (const m of text.matchAll(/var\((--[\w-]+)/g)) {
        if (!declared.has(m[1])) violations.push(`${file.replace(SRC, "src")}: var(${m[1]})`);
      }
    }
    expect(violations).toEqual([]);
  });
});
