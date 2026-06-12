import type { Meta, StoryObj } from "@storybook/react-vite";
import { InkBleedDefs } from "./InkBleedDefs";
import { VerdictStamp } from "./VerdictStamp";

const meta = {
  title: "Patterns/Stationery/InkBleedDefs",
  component: InkBleedDefs,
  parameters: {
    docs: {
      description: {
        component:
          "The shared SVG `<defs>` providing the `#ink-bleed` filter — the mottled, eroded ink " +
          "coverage every stamp wears (`filter: url(#ink-bleed)` in `.stamp`). Mounted once per " +
          "document (the preview decorator and App both mount it); it renders nothing visible " +
          "itself. The specimen below shows the same stamp with the defs present — remove them " +
          "and the stamp prints flat, which is how you detect a missing mount.",
      },
    },
  },
} satisfies Meta<typeof InkBleedDefs>;
export default meta;

type Story = StoryObj<typeof meta>;

export const FilterSpecimen: Story = {
  render: () => (
    <div>
      <InkBleedDefs />
      <p style={{ display: "flex", gap: "var(--space-4)" }}>
        <VerdictStamp verdict="reclaim" seed="ink.bleed.specimen" />
        <VerdictStamp verdict="keep" seed="ink.bleed.specimen.2" />
      </p>
      <p className="eyebrow">the mottle on these stamps IS the #ink-bleed filter at work</p>
    </div>
  ),
};
