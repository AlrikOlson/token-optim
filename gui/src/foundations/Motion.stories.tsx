import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { VerdictStamp } from "../components/VerdictStamp";
import { DeclTable, FoundationsSheet } from "./specimens";
import { tokensIn } from "./tokens-data";

const meta = {
  title: "Foundations/Motion",
  parameters: {
    docs: {
      description: {
        component:
          "Motion is mechanical: stamp and thunk, never float or ease-in-out. Three durations " +
          "(`--motion-snap` 60ms, `--motion-flight` 240ms, `--motion-meter` 360ms) and three " +
          "curves — `--ease-thunk` (the strike), `--ease-settle` (the landing), and " +
          "`--ease-spring`, the true thunk-and-settle spring sampled as `linear()` for view " +
          "transitions (Act I). `prefers-reduced-motion` zeroes every duration and disables " +
          "stamp/view-transition animation — the physics are an enhancement, never a requirement.",
      },
    },
  },
} satisfies Meta;
export default meta;

export const Physics: StoryObj = {
  render: () => (
    <FoundationsSheet
      heading="Stamp & Thunk"
      preamble="The stamps below land with the real animation (reduced-motion renders them instantly). Durations and curves are live from the stylesheet."
    >
      <p style={{ display: "flex", gap: "var(--space-4)", alignItems: "center" }}>
        <VerdictStamp verdict="keep" seed="foundations.keep" />
        <VerdictStamp verdict="review" seed="foundations.review" />
        <VerdictStamp verdict="reclaim" seed="foundations.reclaim" />
      </p>
      <hr className="rule-double" style={{ marginTop: "var(--space-6)" }} />
      <DeclTable tokens={tokensIn("motion")} caption="Motion tokens on file" />
    </FoundationsSheet>
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("--ease-spring")).toBeInTheDocument();
    expect(tokensIn("motion").length).toBeGreaterThanOrEqual(6);
  },
};
