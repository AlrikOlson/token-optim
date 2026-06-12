import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import spec from "../rules-spec.json";
import { RulesPanel } from "./RulesPanel";

describe("RulesPanel — the stated rules cannot drift from the spec", () => {
  it("renders every stated rule verbatim from rules-spec.json, in order", () => {
    render(<RulesPanel defaultOpen />);
    const panel = screen.getByTestId("rules-panel");
    const verdicts = within(panel)
      .getAllByRole("term")
      .map((el) => el.textContent);
    const descriptions = within(panel)
      .getAllByRole("definition")
      .map((el) => el.textContent);
    expect(verdicts).toEqual(spec.stated.map((s) => s.verdict));
    expect(descriptions).toEqual(spec.stated.map((s) => s.description));
  });

  it("is a disclosure: summary present, content behind it", () => {
    render(<RulesPanel />);
    const panel = screen.getByTestId("rules-panel");
    expect(panel).not.toHaveAttribute("open");
    expect(within(panel).getByText("How verdicts are decided")).toBeInTheDocument();
  });

  it("contains no VerdictStamp (stamps render true values, never examples)", () => {
    const { container } = render(<RulesPanel defaultOpen />);
    expect(container.querySelector(".stamp")).toBeNull();
  });
});
