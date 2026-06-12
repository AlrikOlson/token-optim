import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { ReportPreview } from "./ReportPreview";
import { caveats, seats } from "./fixtures";

const meta = {
  title: "Objects/Report/ReportPreview",
  component: ReportPreview,
  parameters: {
    docs: {
      description: {
        component:
          "The client-facing deliverable, rendered live during the seal ceremony and frozen in " +
          "the archive. HARD REGISTER BOUNDARY: this surface never speaks Committee — no wry " +
          "lines, no bureaucratic parody; it is the straight document an MSP forwards to their " +
          "client under their own brand (BrandChip), with the locked data caveats " +
          "(CaveatBlock) attached. The savings figure is the domain's exact arithmetic.",
      },
    },
  },
} satisfies Meta<typeof ReportPreview>;
export default meta;

type Story = StoryObj<typeof meta>;

export const ClientDeliverableDark: Story = {
  globals: { theme: "dark" },
  args: {
    seats,
    mspName: "Northwind IT Partners",
    clientName: "Fabrikam Manufacturing",
    caveats,
  },
};

export const ClientDeliverable: Story = {
  args: {
    seats,
    mspName: "Northwind IT Partners",
    clientName: "Fabrikam Manufacturing",
    caveats,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // Hard register boundary: the deliverable never speaks Committee.
    await expect(canvas.queryByText(/NOTICE:/)).not.toBeInTheDocument();
    await expect(canvas.queryByText(/committee/i)).not.toBeInTheDocument();
    // And the money is the domain's exact number (30+30+19).
    await expect(canvas.getByTestId("report-savings")).toHaveTextContent("$79/month");
  },
};
