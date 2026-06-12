import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";
import { APP_PURPOSE, GLOSSARY } from "../clarity";
import { EmptyState } from "./EmptyState";
import { FirstRunSlip } from "./FirstRunSlip";
import { Gloss } from "./Gloss";

const meta = {
  title: "Patterns/Clarity/Gloss",
  component: Gloss,
  parameters: {
    docs: {
      description: {
        component:
          "The clarity layer (gui-14): the Federal Memo voice is the brand, but it never " +
          "carries the explanation burden alone. A Gloss wraps a Memo-register term with its " +
          "plain meaning — semantic <abbr>, hover/tap/focus reachable, sourced from the ONE " +
          "glossary in clarity.ts so a term can't mean two things on two screens. Use on " +
          "every domain term a first-time viewer meets (docket, verdict, seal, QBR…); never " +
          "gloss plain language.",
      },
    },
  },
} satisfies Meta<typeof Gloss>;
export default meta;

type Story = StoryObj<typeof meta>;

export const GlossedTerm: Story = {
  args: { term: "seal", children: "SEALED & DELIVERED" },
  render: () => (
    <p>
      This month is <Gloss term="sealed">SEALED &amp; DELIVERED</Gloss> — hover or focus the
      term for the plain meaning.
    </p>
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const abbr = canvas.getByText(/SEALED & DELIVERED/);
    await expect(abbr).toHaveAttribute("title", GLOSSARY.sealed);
    // keyboard-reachable: the gloss is not hover-only
    await expect(abbr).toHaveAttribute("tabindex", "0");
  },
};

export const FirstRun: Story = {
  args: { term: "seal", children: "x" },
  render: () => <FirstRunSlip persistent={false} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // the two true sentences, then dismissal removes the slip
    await expect(canvas.getByTestId("first-run")).toHaveTextContent(APP_PURPOSE);
    await userEvent.click(canvas.getByTestId("first-run-dismiss"));
    await expect(canvas.queryByTestId("first-run")).not.toBeInTheDocument();
  },
};

export const EmptySpace: Story = {
  args: { term: "seal", children: "x" },
  render: () => (
    <EmptyState
      what="No decisions yet"
      how="Each seat you decide on the stand above lands here as a ledger row, stamped with its verdict."
    />
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole("status")).toHaveTextContent("No decisions yet");
  },
};
