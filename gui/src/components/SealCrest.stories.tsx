import type { Meta, StoryObj } from "@storybook/react-vite";
import { SealCrest } from "./SealCrest";

const meta = {
  title: "Patterns/Stationery/SealCrest",
  component: SealCrest,
  parameters: {
    docs: {
      description: {
        component:
          "The embossed period seal pressed onto a sealed snapshot. Appears only on sealed " +
          "artifacts (archive tiles, the seal ceremony, the QBR pack) — a crest on an unsealed " +
          "document would be a lie, so the component takes the period it certifies and nothing " +
          "else. Lighting and emboss come from the photoreal pass (gui-6); dark mode renders " +
          "it as microfiche phosphor, not paper.",
      },
    },
  },
} satisfies Meta<typeof SealCrest>;
export default meta;

type Story = StoryObj<typeof meta>;

export const JunePeriod: Story = { args: { period: "2026-06" } };
export const PriorPeriod: Story = { args: { period: "2026-03" } };
