import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { DeclTable, FoundationsSheet } from "./specimens";
import { tokensIn } from "./tokens-data";

const meta = {
  title: "Foundations/Spacing & Shape",
  parameters: {
    docs: {
      description: {
        component:
          "Airy editorial density on a 4px base: seven space steps (`--space-1` … `--space-12`). " +
          "Shape law: `--radius` is 0px and stays 0px — paper has corners. Rules come in two " +
          "weights: the 2px double-strike (`.rule-double`, run twice like a real typewriter rule) " +
          "and the hairline (`--rule-hairline`) for ledger rows.",
      },
    },
  },
} satisfies Meta;
export default meta;

const spaces = tokensIn("space").filter((t) => t.name.startsWith("--space"));
const radii = tokensIn("space").filter((t) => t.name.startsWith("--radius"));

export const Scale: StoryObj = {
  render: () => (
    <FoundationsSheet
      heading="Spacing Scale & Shape Law"
      preamble="Each bar's width is the live token value — measured, not illustrated."
    >
      <div className="stack-2" style={{ marginTop: "var(--space-6)" }}>
        {spaces.map((t) => (
          <div key={t.name} style={{ display: "flex", gap: "var(--space-4)", alignItems: "center" }}>
            <span className="t-figure" style={{ width: "7rem" }}>
              {t.name}
            </span>
            <span
              aria-hidden="true"
              style={{
                // data-driven: the bar IS the token under inspection
                width: `var(${t.name})`,
                height: "1rem",
                background: "var(--ink)",
                display: "inline-block",
              }}
            />
            <span className="t-figure muted">{t.light}</span>
          </div>
        ))}
      </div>
      <hr className="rule-double" style={{ marginTop: "var(--space-8)" }} />
      <p className="t-label">Rules</p>
      <hr className="rule-double" />
      <hr style={{ border: "none", borderTop: "1px solid var(--rule-hairline)" }} />
      <DeclTable tokens={radii} caption="Shape tokens (paper has corners)" />
    </FoundationsSheet>
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(spaces.length).toBeGreaterThanOrEqual(7);
    // the shape law holds: every radius token is 0px
    for (const r of radii) expect(r.light).toBe("0px");
    await expect(canvas.getByText("--space-12")).toBeInTheDocument();
  },
};
