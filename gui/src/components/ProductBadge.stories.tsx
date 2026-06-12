import type { Meta, StoryObj } from "@storybook/react-vite";
import { ProductBadge } from "./ProductBadge";

const meta = {
  title: "Objects/Product/ProductBadge",
  component: ProductBadge,
  parameters: {
    docs: {
      description: {
        component:
          "The single-glyph product marker: Ⓜ for Microsoft 365 Copilot, ⓖ for GitHub Copilot. " +
          "Appears wherever a seat or figure is product-specific (verdict rows, filters, QBR " +
          "tables). One component everywhere — a seat's product must read identically on the " +
          "Hearing, the report, and the QBR pack (object-model fidelity).",
      },
    },
  },
} satisfies Meta<typeof ProductBadge>;
export default meta;

type Story = StoryObj<typeof meta>;

export const Microsoft365: Story = { args: { product: "m365" } };
export const GitHub: Story = { args: { product: "github" } };
export const InContext: Story = {
  args: { product: "m365" },
  render: () => (
    <p>
      <ProductBadge product="m365" /> Microsoft 365 · <ProductBadge product="github" /> GitHub
    </p>
  ),
};
