import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DeskMaterial } from "./DeskMaterial";

describe("DeskMaterial — fallback discipline", () => {
  // gui-13: the canvas geometry moved from inline style to the .desk-canvas
  // rule in tokens.css (visibility keyed on [data-active]). jsdom doesn't load
  // the stylesheet, so these assert the contract — class + data attribute —
  // and the browser-mode story verifies the rendered geometry.
  it("stays inactive without WebGPU (jsdom): hidden canvas, CSS desk untouched", () => {
    render(<DeskMaterial />);
    const canvas = screen.getByTestId("desk-material");
    expect(canvas).toHaveAttribute("data-active", "false");
    expect(canvas).toHaveClass("desk-canvas");
    expect(document.documentElement.dataset.material).toBeUndefined();
  });

  it("is decorative: aria-hidden, dressed by the layout-inert .desk-canvas rule", () => {
    render(<DeskMaterial />);
    const canvas = screen.getByTestId("desk-material");
    expect(canvas).toHaveAttribute("aria-hidden", "true");
    expect(canvas).toHaveClass("desk-canvas");
  });
});
