import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { projectedSavings } from "../domain";
import { SavingsMeter } from "./SavingsMeter";
import { seats } from "./fixtures";

const meta = {
  title: "Objects/Savings/SavingsMeter",
  component: SavingsMeter,
  parameters: {
    docs: {
      description: {
        component:
          "The poster figure: projected monthly savings for the period. Renders " +
          "`projectedSavings()` output ONLY — the meter is an instrument, not an illustration, " +
          "and values never lie even mid-animation (the count-up is driven by the true total). " +
          "One per screen at most; if you need a second money figure, it's a `t-figure`, not " +
          "a meter.",
      },
    },
  },
} satisfies Meta<typeof SavingsMeter>;
export default meta;

type Story = StoryObj<typeof meta>;

export const FromRealVerdicts: Story = {
  args: { monthlyUsd: projectedSavings(seats) },
  play: async ({ canvasElement }) => {
    // Values never lie: the meter shows exactly the domain arithmetic.
    await expect(
      within(canvasElement).getByTestId("savings-value"),
    ).toHaveTextContent("$79");
  },
};

export const Zero: Story = {
  args: { monthlyUsd: 0 },
};
