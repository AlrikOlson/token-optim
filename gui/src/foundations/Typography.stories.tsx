import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { DeclTable, FoundationsSheet } from "./specimens";
import { TYPE_SCALE, tokensIn } from "./tokens-data";

const meta = {
  title: "Foundations/Typography",
  parameters: {
    docs: {
      description: {
        component:
          "Two typefaces, six sizes, no exceptions. Archivo (incl. Black) is the display voice — " +
          "mastheads, stamps, labels, always uppercase with `--track-caps` tracking. IBM Plex Mono " +
          "is the evidence voice — figures, exhibits, reference numbers, always tabular-nums. " +
          "THE SYSTEM (gui-6d): components may only use the `t-*` classes below; a `font-size` " +
          "in a component file is a violation. Specimens render with the real classes, so what " +
          "you see is what the stylesheet enforces.",
      },
    },
  },
} satisfies Meta;
export default meta;

export const TypeScale: StoryObj = {
  render: () => (
    <FoundationsSheet
      heading="The Six Authorized Sizes"
      preamble="Each specimen below wears its system class. There is no seventh size."
    >
      <div className="stack-4" style={{ marginTop: "var(--space-6)" }}>
        {TYPE_SCALE.map(({ cls, role }) => (
          <div key={cls}>
            <p className="eyebrow">
              .{cls} — {role}
            </p>
            <p className={`${cls} press`} style={{ margin: 0, overflowWrap: "anywhere" }}>
              {cls.startsWith("t-figure") ? "$1,234,567.00" : "Bureau of Seat Affairs"}
            </p>
          </div>
        ))}
      </div>
      <hr className="rule-double" style={{ marginTop: "var(--space-8)" }} />
      <DeclTable tokens={tokensIn("type")} caption="Type tokens on file" />
    </FoundationsSheet>
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    for (const { cls } of TYPE_SCALE) {
      await expect(canvas.getByText(new RegExp(`^\\.${cls} `))).toBeInTheDocument();
    }
    // the scale really is six steps (+ the lg figure variant)
    expect(TYPE_SCALE.length).toBe(7);
  },
};
