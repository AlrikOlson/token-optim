/** Specimen components for the Foundations catalog. Catalog-only — never
 * imported by app code. Styled with the same system classes they document. */
import type { ReactNode } from "react";
import type { TokenDecl } from "./tokens-data";

/** A color swatch row: chip + name + declared values. The label sits BESIDE
 * the chip (never on it) so axe contrast rules hold for every ink. */
export function Swatch({ token }: { token: TokenDecl }) {
  return (
    <tr>
      <td>
        <span
          aria-hidden="true"
          style={{
            // data-driven: the chip IS the token under inspection
            background: `var(${token.name})`,
            display: "inline-block",
            width: "3.5rem",
            height: "2rem",
            border: "1px solid var(--rule-hairline)",
            verticalAlign: "middle",
          }}
        />
      </td>
      <td className="t-figure">{token.name}</td>
      <td className="t-figure muted">{token.light}</td>
      <td className="t-figure muted">{token.dark ?? "— (inherits)"}</td>
    </tr>
  );
}

export function SwatchTable({ tokens, caption }: { tokens: TokenDecl[]; caption: string }) {
  return (
    <table className="ledger">
      <caption className="eyebrow" style={{ textAlign: "left", padding: "var(--space-2) 0" }}>
        {caption}
      </caption>
      <thead>
        <tr>
          <th>Specimen</th>
          <th>Token</th>
          <th>Light (manila)</th>
          <th>Dark (microfiche)</th>
        </tr>
      </thead>
      <tbody>
        {tokens.map((t) => (
          <Swatch key={t.name} token={t} />
        ))}
      </tbody>
    </table>
  );
}

/** A plain declared-value table for non-color tokens (type, motion, texture). */
export function DeclTable({ tokens, caption }: { tokens: TokenDecl[]; caption: string }) {
  return (
    <table className="ledger">
      <caption className="eyebrow" style={{ textAlign: "left", padding: "var(--space-2) 0" }}>
        {caption}
      </caption>
      <thead>
        <tr>
          <th>Token</th>
          <th>Declared value</th>
        </tr>
      </thead>
      <tbody>
        {tokens.map((t) => (
          <tr key={t.name}>
            <td className="t-figure">{t.name}</td>
            <td className="t-figure muted" style={{ overflowWrap: "anywhere" }}>
              {t.light.length > 90 ? `${t.light.slice(0, 90)}…` : t.light}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** The standard Foundations page frame: a sheet with a memo-voice preamble. */
export function FoundationsSheet({
  heading,
  preamble,
  children,
}: {
  heading: string;
  preamble: string;
  children: ReactNode;
}) {
  return (
    <div className="sheet" style={{ padding: "var(--space-6) var(--space-8)", maxWidth: 880 }}>
      <p className="eyebrow">DESIGN LAW — FEDERAL MEMO, 1968 · FOUNDATIONS</p>
      <h1 className="t-title press">{heading}</h1>
      <hr className="rule-double" />
      <p className="muted" style={{ maxWidth: "62ch" }}>
        {preamble}
      </p>
      {children}
    </div>
  );
}
