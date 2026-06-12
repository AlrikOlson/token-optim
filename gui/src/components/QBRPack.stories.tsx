import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { QBRPack } from "./QBRPack";

const meta = {
  title: "Objects/QBRPack/QBRPack",
  component: QBRPack,
  parameters: {
    docs: {
      description: {
        component:
          "The quarterly deliverable assembled exclusively from SEALED period snapshots — it " +
          "cannot contain unsealed data by construction (the selector only yields sealed " +
          "months). This is the history moat in the costume MSPs already pay for: quarter " +
          "story, seat delta, dollars reclaimed. Client register throughout — straight " +
          "document, no Committee voice.",
      },
    },
  },
} satisfies Meta<typeof QBRPack>;
export default meta;

type Story = StoryObj<typeof meta>;

export const QuarterFromSealedMonths: Story = {
  args: {
    clientName: "Contoso Ltd",
    quarter: "Q2 2026",
    snapshots: [
      { period: "2026-04", savingsUsd: 120, sealed: true },
      { period: "2026-05", savingsUsd: 150, sealed: true },
      { period: "2026-06", savingsUsd: 120, sealed: true },
    ],
  },
  play: async ({ canvasElement }) => {
    await expect(
      within(canvasElement).getByTestId("qbr-total"),
    ).toHaveTextContent("$390");
  },
};
