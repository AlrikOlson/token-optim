import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { FoundationsSheet, SwatchTable } from "./specimens";
import { tokensIn } from "./tokens-data";

const meta = {
  title: "Foundations/Color",
  parameters: {
    docs: {
      description: {
        component:
          "Every ink and stock the Bureau is authorized to use. Swatches and values are parsed " +
          "from `tokens.css` itself — this page cannot drift from the law. Light theme is handled " +
          "manila under carbon ink; dark theme is microfiche (green-tinted near-black, phosphor ink). " +
          "Verdict inks are reserved for verdicts: ledger green = keep, clerk amber = review, " +
          "stamp red = reclaim. Ballpoint blue is the only accent. `--ink-faint` is decorative " +
          "only — never body text (AA holds in both themes).",
      },
    },
  },
} satisfies Meta;
export default meta;

const colors = tokensIn("color");

export const Palette: StoryObj = {
  render: () => (
    <FoundationsSheet
      heading="Authorized Inks & Stocks"
      preamble="The full palette, live from the stylesheet. The dark column shows the microfiche override; tokens without one inherit their manila value."
    >
      <SwatchTable tokens={colors} caption={`${colors.length} color tokens on file`} />
    </FoundationsSheet>
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // the catalog renders from the parsed stylesheet — prove it's non-empty
    // and that the core stocks made it through the parser
    // 14 inks & stocks on file as of gui-12 (vignette/grain are texture)
    expect(colors.length).toBeGreaterThanOrEqual(14);
    for (const name of ["--paper", "--ink", "--verdict-reclaim", "--accent", "--desk"]) {
      await expect(canvas.getByText(name)).toBeInTheDocument();
    }
  },
};
