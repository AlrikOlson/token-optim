import type { Meta, StoryObj } from "@storybook/react-vite";
import { ClientTile } from "./ClientTile";

const meta = {
  title: "Objects/Client/ClientTile",
  component: ClientTile,
  parameters: {
    docs: {
      description: {
        component:
          "A client's index card on the Run Board. Its stage is DERIVED state — awaiting-data " +
          "→ verdicts-in → in-review → sealed & delivered — never stored separately, so the " +
          "board cannot disagree with the hearings. Data-rich by design (gui-6c): true seat " +
          "counts, cases remaining, sealed savings. A sealed tile opens the read-only archive; " +
          "an in-review tile convenes the Hearing.",
      },
    },
  },
} satisfies Meta<typeof ClientTile>;
export default meta;

type Story = StoryObj<typeof meta>;

export const AwaitingData: Story = {
  args: { client: { name: "Fabrikam Manufacturing", stage: "awaiting-data" } },
};

export const InReview: Story = {
  args: {
    client: { name: "Contoso Ltd", stage: "in-review", casesRemaining: 6 },
  },
};

export const Sealed: Story = {
  args: {
    client: { name: "Tailspin Toys", stage: "sealed", sealedSavingsUsd: 270 },
  },
};
