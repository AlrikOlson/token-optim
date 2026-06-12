import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { VerdictRow } from "./VerdictRow";
import { seats } from "./fixtures";

const meta = {
  title: "Objects/SeatRecommendation/VerdictRow",
  component: VerdictRow,
  parameters: {
    docs: {
      description: {
        component:
          "One seat's case in the ledger: user, product badge, evidence summary, verdict stamp, " +
          "and the monthly figure. THE place a SeatRecommendation renders — the Hearing, the " +
          "decided ledger, and the archive all use this same row (object-model fidelity). " +
          "Voice rules: the wry NOTICE line renders only for reclaim-grade verdicts, only from " +
          "a typed payload carrying the true value, and `plain` disables it entirely (the " +
          "high-row-count fallback). Keep/review evidence stays plain — register restraint.",
      },
    },
  },
  decorators: [
    (Story) => (
      <table>
        <tbody>
          <Story />
        </tbody>
      </table>
    ),
  ],
} satisfies Meta<typeof VerdictRow>;
export default meta;

type Story = StoryObj<typeof meta>;

export const ReclaimNeverUsed: Story = {
  args: { seat: seats[3] },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // Voice slot proof: the wry line exists AND carries the true value.
    await expect(
      canvas.getByText(/NOTICE:.*\$30/),
    ).toBeInTheDocument();
  },
};

export const ReclaimIdle: Story = {
  args: { seat: seats[2] },
};

export const KeepActive: Story = {
  args: { seat: seats[0] },
  play: async ({ canvasElement }) => {
    // Register restraint: keep rows are plain.
    await expect(
      within(canvasElement).queryByText(/NOTICE:/),
    ).not.toBeInTheDocument();
  },
};

export const PlainFallback: Story = {
  args: { seat: seats[3], plain: true },
  play: async ({ canvasElement }) => {
    await expect(
      within(canvasElement).queryByText(/NOTICE:/),
    ).not.toBeInTheDocument();
  },
};

export const EditableGithubSeat: Story = {
  args: { seat: seats[4], onVerdict: () => {} },
};

export const ReclaimNeverUsedDark: Story = {
  globals: { theme: "dark" },
  args: { seat: seats[3] },
};
