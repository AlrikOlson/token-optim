import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { EvidencePanel } from "./EvidencePanel";
import { seats } from "./fixtures";

const meta = {
  title: "Objects/SeatRecommendation/EvidencePanel",
  component: EvidencePanel,
  parameters: {
    docs: {
      description: {
        component:
          "The typewriter form block presenting a seat's evidence: last activity, app usage, " +
          "monthly cost. Register rule (blueprint §6.5): the panel is PLAIN — Committee voice " +
          "never renders here, and a nil `last_activity_at` is phrased exactly as " +
          "'no activity on record (vendor retains 90 days)' because the vendor erases the " +
          "evidence, not the seat. Values come from the seat object; nothing is invented.",
      },
    },
  },
} satisfies Meta<typeof EvidencePanel>;
export default meta;

type Story = StoryObj<typeof meta>;

export const NeverUsed: Story = {
  args: { seat: seats[3] },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // Register-free by construction; vendor-retention phrasing is plain.
    await expect(canvas.queryByText(/NOTICE:/)).not.toBeInTheDocument();
    await expect(
      canvas.getByText(/no activity on record \(vendor retains 90 days\)/),
    ).toBeInTheDocument();
  },
};

export const ActiveSeat: Story = { args: { seat: seats[0] } };
export const IdleSeat: Story = { args: { seat: seats[2] } };
