import type { Meta, StoryObj } from "@storybook/react-vite";
import { SnapshotPoint } from "./SnapshotPoint";

const meta = {
  title: "Objects/PeriodSnapshot/SnapshotPoint",
  component: SnapshotPoint,
  parameters: {
    docs: {
      description: {
        component:
          "One period in the EXHIBIT history strip. A sealed point is immutable history — the " +
          "snapshot moat made visible: vendors retain ~90 days, sealed snapshots remember " +
          "forever. The open (unsealed) point is the current period still in session. " +
          "Savings figures are the snapshot's true `savingsUsd`; the strip doubles as the " +
          "scroll-progress instrument on the Hearing (Act II), and even there values never lie.",
      },
    },
  },
} satisfies Meta<typeof SnapshotPoint>;
export default meta;

type Story = StoryObj<typeof meta>;

export const Sealed: Story = {
  args: { snapshot: { period: "2026-05", savingsUsd: 150, sealed: true } },
};
export const OpenPeriod: Story = {
  args: { snapshot: { period: "2026-06", savingsUsd: 0, sealed: false } },
};
export const QuarterStrip: Story = {
  args: { snapshot: { period: "2026-04", savingsUsd: 120, sealed: true } },
  render: () => (
    <p>
      <SnapshotPoint snapshot={{ period: "2026-04", savingsUsd: 120, sealed: true }} />
      <SnapshotPoint snapshot={{ period: "2026-05", savingsUsd: 150, sealed: true }} />
      <SnapshotPoint snapshot={{ period: "2026-06", savingsUsd: 0, sealed: false }} />
    </p>
  ),
};
