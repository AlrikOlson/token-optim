/** Foundations data — parsed from tokens.css ITSELF (`?raw`), never copied.
 *
 * The catalog renders whatever the stylesheet declares, so the Foundations
 * pages cannot drift from the design law: add a token and it appears in
 * Storybook; remove one and it disappears. Same principle as voice.ts —
 * documentation can only render from a backing true value.
 */
import tokensCss from "../tokens.css?raw";

export interface TokenDecl {
  /** custom property name, e.g. "--paper" */
  name: string;
  /** declared value in :root (light) */
  light: string;
  /** declared value in [data-theme="dark"], if overridden */
  dark?: string;
}

export function declarationsOf(block: string): Map<string, string> {
  const out = new Map<string, string>();
  // strip comments so a commented-out token never documents itself
  const code = block.replace(/\/\*[\s\S]*?\*\//g, "");
  // values may span lines (gradients, linear(), data: URLs) — split on ";"
  for (const stmt of code.split(";")) {
    const m = stmt.match(/(--[\w-]+)\s*:\s*([\s\S]+)/);
    if (m) out.set(m[1], m[2].trim().replace(/\s+/g, " "));
  }
  return out;
}

/** Grab the body of the first `selector { ... }` block, brace-balanced. */
export function blockOf(css: string, selector: string): string {
  const start = css.indexOf(selector);
  if (start === -1) return "";
  const open = css.indexOf("{", start);
  let depth = 0;
  for (let i = open; i < css.length; i++) {
    if (css[i] === "{") depth++;
    if (css[i] === "}" && --depth === 0) return css.slice(open + 1, i);
  }
  return "";
}

/** Parse a stylesheet's :root tokens with their dark overrides. Pure — the
 * unit suite feeds it the file directly; the catalog feeds it the `?raw`
 * import below. */
export function parseTokens(css: string): TokenDecl[] {
  const lightDecls = declarationsOf(blockOf(css, ":root"));
  const darkDecls = declarationsOf(blockOf(css, '[data-theme="dark"]'));
  return [...lightDecls.entries()].map(([name, light]) => ({
    name,
    light,
    dark: darkDecls.get(name),
  }));
}

/** Every token declared in :root, with its dark override when one exists.
 * NOTE: vitest's jsdom project intercepts .css imports (even `?raw`) and
 * yields "" — so this constant is only trustworthy in vite/browser contexts.
 * The Foundations stories assert non-emptiness in the browser gate. */
export const allTokens: TokenDecl[] = parseTokens(tokensCss);

/** Group membership by name — the catch-all "other" group guarantees a new
 * token always lands SOMEWHERE in the catalog. */
const GROUPS: ReadonlyArray<{ key: string; match: (n: string) => boolean }> = [
  {
    key: "color",
    match: (n) =>
      /^--(paper|ink|rule|verdict|savings|accent|desk)(?!-vignette|-grain)/.test(n) &&
      !n.startsWith("--paper-grain"),
  },
  { key: "type", match: (n) => /^--(font|size|track)/.test(n) },
  { key: "space", match: (n) => /^--(space|radius)/.test(n) },
  { key: "motion", match: (n) => /^--(motion|ease)/.test(n) },
  {
    key: "texture",
    match: (n) =>
      /^--(grain|fiber|sheet-lie|desk-vignette|paper-grain-alpha)/.test(n),
  },
];

export function groupOf(name: string): string {
  return GROUPS.find((g) => g.match(name))?.key ?? "other";
}

export function tokensIn(key: string): TokenDecl[] {
  return allTokens.filter((t) => groupOf(t.name) === key);
}

/** The six type-scale classes of THE SYSTEM (gui-6d). Class names only —
 * specimens render with the real class, so the sizes come from the live CSS. */
export const TYPE_SCALE = [
  { cls: "t-poster", role: "The poster figure — one per screen, the number that matters." },
  { cls: "t-headline", role: "Screen mastheads. Archivo Black, full caps." },
  { cls: "t-title", role: "Document and case-file titles." },
  { cls: "t-label", role: "Section heads, buttons, column headers." },
  { cls: "t-micro", role: "Stamped reference numbers, eyebrows, footnotes." },
  { cls: "t-figure", role: "Tabular money and counts. Plex Mono, tabular-nums." },
  { cls: "t-figure-lg", role: "The larger ledger figure (meter readouts)." },
] as const;
