import type { Meta, StoryObj } from "@storybook/react-vite";
import { VerdictStamp } from "./VerdictStamp";

const meta = {
  title: "Objects/SeatRecommendation/VerdictStamp",
  component: VerdictStamp,
  parameters: {
    docs: {
      description: {
        component:
          "The rubber stamp a verdict arrives as. All three verdicts are stamps (design law): " +
          "KEEP in ledger green, REVIEW in clerk amber, RECLAIM in stamp red. Tilt is " +
          "deterministic — hashed from `seed` (the seat's user), never random — so the same " +
          "case reads the same on every render and on the Python-rendered report (gui-11: " +
          "demo.py mirrors the same FNV-1a hash, golden-vector tested on both sides). Ink " +
          "mottle comes from the seeded `#ink-bleed-N` SVG filters (Patterns/Stationery/" +
          "InkBleedDefs) — each seat's impression wears a different worn pad, deterministically. " +
          "Use only to render a true verdict value; never decoratively.",
      },
    },
  },
} satisfies Meta<typeof VerdictStamp>;
export default meta;

type Story = StoryObj<typeof meta>;

export const Keep: Story = { args: { verdict: "keep", seed: "maria.chen" } };
export const Review: Story = { args: { verdict: "review", seed: "raj.kumar" } };
export const Reclaim: Story = { args: { verdict: "reclaim", seed: "bob.tanner" } };

export const AllThree: Story = {
  args: { verdict: "keep", seed: "maria.chen" },
  render: () => (
    <p style={{ display: "flex", gap: "var(--space-4)", alignItems: "center" }}>
      <VerdictStamp verdict="keep" seed="maria.chen" />
      <VerdictStamp verdict="review" seed="raj.kumar" />
      <VerdictStamp verdict="reclaim" seed="bob.tanner" />
    </p>
  ),
};

/** gui-11: the same verdict across many seats — every impression tilts and
 * erodes differently (per-seat seeded pad), yet re-renders identically. */
export const PrintShop: Story = {
  args: { verdict: "reclaim", seed: "maria.chen" },
  render: () => (
    <p style={{ display: "flex", gap: "var(--space-4)", flexWrap: "wrap", alignItems: "center" }}>
      {["maria.chen", "raj.kumar", "bob.tanner", "alice.wu", "omar.haddad", "june.park"].map((u) => (
        <VerdictStamp key={u} verdict="reclaim" seed={u} />
      ))}
    </p>
  ),
};
