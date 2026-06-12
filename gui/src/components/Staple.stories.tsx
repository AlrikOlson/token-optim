import type { Meta, StoryObj } from "@storybook/react-vite";
import { Staple } from "./Staple";

const meta = {
  title: "Patterns/Stationery/Staple",
  component: Staple,
  parameters: {
    docs: {
      description: {
        component:
          "The office hardware pinning an attachment to its case file. Pure stationery — " +
          "decorative, carries no data, and therefore disappears in dark mode (a microfiche " +
          "scan has no hardware; `[data-theme=\"dark\"] .staple { display: none }`). Use on " +
          "sheets that are attachments to a primary document, never on the primary itself.",
      },
    },
  },
} satisfies Meta<typeof Staple>;
export default meta;

type Story = StoryObj<typeof meta>;

export const PinnedAttachment: Story = {
  render: () => (
    <div className="sheet" style={{ position: "relative", width: 220, height: 90, marginTop: 20 }}>
      <Staple />
      <p className="mono" style={{ padding: "var(--space-4)", fontSize: "0.8rem" }}>
        attachment, stapled
      </p>
    </div>
  ),
};
