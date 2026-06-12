import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";
import { App } from "../App";
import { reduce, seedState } from "../store";

const meta = {
  title: "Screens/App",
  component: App,
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          "The whole office, end to end: Run Board (period spine + derived client tiles) → " +
          "the Hearing (one seat on the stand, verdicts stamped) → the sincere Seal ceremony → " +
          "the sealed archive and QBR pack. Each story below proves a structural invariant in " +
          "the DOM: the seal stays locked while cases remain, sealed periods are read-only, " +
          "the deliverable surfaces never speak Committee, and a solo book skips the board.",
      },
    },
  },
  // Deterministic by construction: an explicit initial state disables
  // localStorage persistence inside the App (see App.tsx `persistent`).
  args: { initial: seedState() },
} satisfies Meta<typeof App>;
export default meta;

type Story = StoryObj<typeof meta>;

/** The Run Board home: derived columns, true tally, all four voice slots. */
export const RunBoardHome: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText(/June 2026 run/i)).toBeInTheDocument();
    // milestone slot with true counts (0 of 3 sealed this period)
    await expect(canvas.getByTestId("run-tally")).toHaveTextContent("0 of 3");
    // ambient + exhibit slots render true aggregates
    await expect(canvas.getByTestId("ambient-line")).toHaveTextContent(/FINDINGS: \d+% of audited seats/);
    await expect(canvas.getByTestId("exhibit-caption")).toHaveTextContent(/EXHIBIT A: 1 month .* 90 days/);
  },
};

export const RunBoardDark: Story = {
  globals: { theme: "dark" },
};

/** Opening a client convenes the Hearing; the seal is locked until all
 * cases are heard — the structural invariant, asserted in the DOM. */
export const HearingSealLocked: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByText("Contoso Ltd"));
    await expect(canvas.getByTestId("the-stand")).toBeInTheDocument();
    const seal = canvas.getByTestId("seal-button");
    await expect(seal).toBeDisabled();
    await expect(seal).toHaveTextContent(/cases remaining/);
    // nil-activity case phrases the vendor-retention truth, register-free
    await userEvent.click(canvas.getByText(/accept all suggested/i));
    await expect(canvas.getByTestId("seal-button")).toBeEnabled();
  },
};

/** Full happy path: accept-all → seal flow (sincere, voice-free) → exhale
 * on the board afterward. */
export const SealCeremony: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByText("Contoso Ltd"));
    await userEvent.click(canvas.getByText(/accept all suggested/i));
    await userEvent.click(canvas.getByTestId("seal-button"));
    // The Seal screen is sincere: zero Committee voice anywhere.
    await expect(canvas.queryByText(/NOTICE:/)).not.toBeInTheDocument();
    await expect(canvas.queryByText(/committee/i)).not.toBeInTheDocument();
    await expect(canvas.getByText(/cannot be edited afterward/)).toBeInTheDocument();
    await userEvent.click(canvas.getByTestId("seal-confirm"));
    // Back on the board: tile sealed, exhale line lands AFTER the confirm.
    await expect(canvas.getByTestId("run-tally")).toHaveTextContent("1 of 3");
    await expect(canvas.getByText(/herewith returned to the general fund/)).toBeInTheDocument();
  },
};

/** Solo path: a one-client book lands straight in the Hearing. */
export const SoloPathSkipsBoard: Story = {
  args: {
    initial: {
      ...seedState(),
      clients: seedState().clients.filter((c) => c.id === "contoso"),
    },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByTestId("the-stand")).toBeInTheDocument();
    await expect(canvas.queryByText(/June 2026 run/i)).not.toBeInTheDocument();
  },
};

/** The QBR pack assembles from sealed months only and is client-ready:
 * zero Committee voice anywhere in the deliverable view. */
export const QBRPackFromBoard: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // contoso has a sealed 2026-05 → a Q2 2026 QBR entry exists
    await userEvent.click(canvas.getByText(/Contoso Ltd · Q2 2026 QBR pack/));
    await expect(canvas.getByTestId("qbr-total")).toHaveTextContent("$150");
    await expect(canvas.getByText(/1 sealed month/)).toBeInTheDocument();
    await expect(canvas.queryByText(/NOTICE:/)).not.toBeInTheDocument();
    await expect(canvas.queryByText(/committee/i)).not.toBeInTheDocument();
    // June is unsealed — it must not appear in the pack
    await expect(canvas.queryByText(/2026-06/)).not.toBeInTheDocument();
  },
};

/** gui-14 acceptance: the cold-viewer path. Every screen states its purpose
 * in plain language without interaction; the first-run slip explains the
 * whole tool and dismisses; the empty ledger explains itself. */
export const ColdViewerClarity: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // Run Board: subtitle + the two-sentence purpose, then dismiss sticks
    await expect(canvas.getByTestId("screen-sub")).toHaveTextContent(/one card per client/i);
    await expect(canvas.getByTestId("first-run")).toHaveTextContent(/nobody is using/);
    await userEvent.click(canvas.getByTestId("first-run-dismiss"));
    await expect(canvas.queryByTestId("first-run")).not.toBeInTheDocument();
    // glossed Memo terms carry plain meanings (title attr from ONE glossary)
    const sealedCol = canvas.getByText("Sealed & delivered");
    await expect(sealedCol).toHaveAttribute("title", expect.stringContaining("locked"));
    // Hearing: subtitle + the empty ledger explains where rows come from
    await userEvent.click(canvas.getByText("Contoso Ltd"));
    await expect(canvas.getByTestId("screen-sub")).toHaveTextContent(/keep, review, or reclaim/i);
    await expect(canvas.getByText(/No decisions yet/)).toBeInTheDocument();
    // Seal: subtitle states the lock in plain terms
    await userEvent.click(canvas.getByText(/accept all suggested/i));
    await userEvent.click(canvas.getByTestId("seal-button"));
    await expect(canvas.getByTestId("screen-sub")).toHaveTextContent(/locks this month/i);
  },
};

/** A sealed client's tile opens the ARCHIVED report — read-only, rendered
 * from the frozen snapshot, never an editable hearing. */
export const SealedTileOpensArchive: Story = {
  args: {
    initial: (() => {
      let s = seedState();
      s = reduce(s, { type: "accept-all-suggested", clientId: "contoso" });
      s = reduce(s, { type: "seal", clientId: "contoso", sealedAt: "2026-06-30T00:00:00Z" });
      return s;
    })(),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByText("Contoso Ltd"));
    // the archive, not a hearing: frozen report, no stand, no verdict controls
    await expect(canvas.queryByTestId("the-stand")).not.toBeInTheDocument();
    await expect(canvas.getByTestId("sealed-at")).toHaveTextContent(/cannot change/);
    await expect(canvas.getByTestId("report-savings")).toBeInTheDocument();
    await expect(canvas.queryByRole("combobox")).not.toBeInTheDocument();
    await expect(canvas.queryByText(/NOTICE:/)).not.toBeInTheDocument();
  },
};
