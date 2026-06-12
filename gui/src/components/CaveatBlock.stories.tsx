import type { Meta, StoryObj } from "@storybook/react-vite";
import { CaveatBlock } from "./CaveatBlock";
import { caveats } from "./fixtures";

const meta = {
  title: "Objects/Report/CaveatBlock",
  component: CaveatBlock,
  parameters: {
    docs: {
      description: {
        component:
          "The data-caveats footnote of the report: where the activity data comes from and " +
          "what the vendor retains. Caveats are LOCKED copy (pv-2/pv-3) — they state the " +
          "telemetry's real limits (e.g. GitHub retains ~90 days of last-activity) and ship " +
          "on every client-facing report. Client register: plain language, no Committee voice.",
      },
    },
  },
} satisfies Meta<typeof CaveatBlock>;
export default meta;

type Story = StoryObj<typeof meta>;

export const StandardCaveats: Story = { args: { caveats } };
export const SingleCaveat: Story = { args: { caveats: [caveats[0]] } };
