import type { Meta, StoryObj } from "@storybook/react-vite";
import { BrandChip } from "./BrandChip";

const meta = {
  title: "Objects/Report/BrandChip",
  component: BrandChip,
  parameters: {
    docs: {
      description: {
        component:
          "The MSP's brand mark on the deliverable — name plus accent swatch. This is the " +
          "'branded report' half of the product promise: the report goes out under the MSP's " +
          "identity, not ours. The accent color is the only place a non-token color is " +
          "permitted, because it is DATA (the customer's brand), not design.",
      },
    },
  },
} satisfies Meta<typeof BrandChip>;
export default meta;

type Story = StoryObj<typeof meta>;

export const Northwind: Story = {
  args: { mspName: "Northwind IT Partners", accent: "#7a3ff2" },
};
export const LongName: Story = {
  args: { mspName: "Consolidated Municipal Technology Services Cooperative", accent: "#0f766e" },
};
