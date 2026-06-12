import type { Meta, StoryObj } from "@storybook/react-vite";
import { DeskMaterial } from "./DeskMaterial";

const meta = {
  title: "Patterns/Scene/DeskMaterial",
  component: DeskMaterial,
  parameters: {
    docs: {
      description: {
        component:
          "Act III's WebGPU desk: normal-mapped paper grain under a directional lamp, rendered " +
          "to a fixed canvas behind the document. Strict progressive enhancement — feature-" +
          "detected, never participates in layout, and the CSS desk (tokens `--desk`, " +
          "`--desk-vignette`, `--grain`) remains the automatic fallback everywhere WebGPU is " +
          "absent, including this story under headless Chromium. When the GPU material is live, " +
          "`[data-material=\"gpu\"]` steps the CSS desk aside.",
      },
    },
  },
} satisfies Meta<typeof DeskMaterial>;
export default meta;

type Story = StoryObj<typeof meta>;

export const MaterialOrFallback: Story = {
  render: () => (
    <div style={{ minHeight: 160 }}>
      <DeskMaterial />
      <p className="mono" style={{ fontSize: "0.8rem", color: "var(--ink-muted)" }}>
        the WebGPU desk renders behind this text when the GPU is available; otherwise the CSS
        desk you see IS the fallback
      </p>
    </div>
  ),
};
