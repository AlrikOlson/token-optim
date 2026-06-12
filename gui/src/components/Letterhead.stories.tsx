import type { Meta, StoryObj } from "@storybook/react-vite";
import { Letterhead } from "./Letterhead";

const meta = {
  title: "Patterns/Stationery/Letterhead",
  component: Letterhead,
  parameters: {
    docs: {
      description: {
        component:
          "The Bureau masthead — on every screen, per design law. Carries the period and the " +
          "session status line. On scroll it compresses to a slim classification bar and its " +
          "underline becomes the docket-progress rule, a TRUE instrument: scaleX is the real " +
          "scroll position (values never lie, even decorative ones). Stationery, not a domain " +
          "object: it frames documents and never carries data of its own beyond period/status.",
      },
    },
  },
} satisfies Meta<typeof Letterhead>;
export default meta;

type Story = StoryObj<typeof meta>;

export const InSession: Story = { args: { period: "2026-06", status: "IN SESSION" } };
export const SealedSession: Story = { args: { period: "2026-05", status: "SEALED & DELIVERED" } };
