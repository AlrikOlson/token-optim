import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { DeclTable, FoundationsSheet } from "./specimens";
import { tokensIn } from "./tokens-data";

const meta = {
  title: "Foundations/Texture & Material",
  parameters: {
    docs: {
      description: {
        component:
          "The scene law (gui-6): the viewport is a photographed desk and every element belongs " +
          "to a physical object lying on it — nothing floats in a void. `--grain` and `--fiber` " +
          "are tiled SVG turbulence (paper stock); `--sheet-lie` is the contact-plus-ambient " +
          "shadow of a sheet that LIES on the desk (paper doesn't float, so there are no soft " +
          "UI shadows). Surface classes: `.sheet` (a sheet on the desk), `.slip` (a smaller memo " +
          "slip), `.lies` (per-instance deterministic tilt via `--lie-tilt`). In dark mode the " +
          "scene becomes microfiche film: no desk, no hardware, no lie shadows.",
      },
    },
  },
} satisfies Meta;
export default meta;

export const Surfaces: StoryObj = {
  render: () => (
    <FoundationsSheet
      heading="Stock, Grain & The Desk"
      preamble="Specimen surfaces below are the real classes — grain, fiber, and shadows come from the live tokens."
    >
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "var(--space-6)",
          marginTop: "var(--space-6)",
        }}
      >
        <div className="sheet" style={{ padding: "var(--space-4)", minHeight: 110 }}>
          <p className="t-label">.sheet</p>
          <p className="muted" style={{ margin: 0 }}>
            A sheet of paper laid on the desk: grain plus handled-edge darkening.
          </p>
        </div>
        <div className="slip" style={{ minHeight: 110 }}>
          <p className="t-label">.slip</p>
          <p className="muted" style={{ margin: 0 }}>
            A smaller memo slip beside the main document — pre-tilted −0.35°.
          </p>
        </div>
        <div
          className="sheet lies"
          style={{ padding: "var(--space-4)", minHeight: 110, ["--lie-tilt" as string]: "1.2deg" }}
        >
          <p className="t-label">.lies</p>
          <p className="muted" style={{ margin: 0 }}>
            An object lying on another; tilt is data-driven and deterministic.
          </p>
        </div>
        <div
          aria-hidden="true"
          style={{
            background: "var(--desk)",
            backgroundImage: "var(--desk-vignette), var(--grain)",
            minHeight: 110,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <span className="t-label" style={{ color: "#efe4cc" }}>
            --desk (steel office green)
          </span>
        </div>
      </div>
      <hr className="rule-double" style={{ marginTop: "var(--space-8)" }} />
      <DeclTable tokens={tokensIn("texture")} caption="Texture tokens on file (values abridged)" />
    </FoundationsSheet>
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    for (const cls of [".sheet", ".slip", ".lies"]) {
      await expect(canvas.getByText(cls)).toBeInTheDocument();
    }
  },
};
