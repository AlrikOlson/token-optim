import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Seat } from "../domain";
import { projectedSavings } from "../domain";
import { CaveatBlock } from "./CaveatBlock";
import { ClientTile } from "./ClientTile";
import { EvidencePanel } from "./EvidencePanel";
import { ProductBadge } from "./ProductBadge";
import { SavingsMeter } from "./SavingsMeter";
import { VerdictRow } from "./VerdictRow";

const reclaimNever: Seat = {
  user: "m.ruiz",
  product: "m365",
  verdict: "reclaim",
  reason: "never used Copilot",
  monthlySavingUsd: 30,
  daysSinceLastActivity: null,
};

const keepActive: Seat = {
  user: "a.chen",
  product: "github",
  verdict: "keep",
  reason: "active, 3 apps in the last month",
  monthlySavingUsd: 0,
  daysSinceLastActivity: 2,
  activeApps: 3,
};

const renderRow = (seat: Seat, plain = false) =>
  render(
    <table>
      <tbody>
        <VerdictRow seat={seat} plain={plain} />
      </tbody>
    </table>,
  );

describe("SavingsMeter — values never lie", () => {
  it("renders the exact figure it is given", () => {
    render(<SavingsMeter monthlyUsd={270} />);
    expect(screen.getByTestId("savings-value")).toHaveTextContent("$270");
  });
  it("renders zero as zero, not as absence", () => {
    render(<SavingsMeter monthlyUsd={0} />);
    expect(screen.getByTestId("savings-value")).toHaveTextContent("$0");
  });
});

describe("VerdictRow — voice boundary", () => {
  it("speaks in register on reclaim rows, via payload only", () => {
    renderRow(reclaimNever);
    // the wry line itself carries the true value
    expect(screen.getByText(/NOTICE:.*\$30/)).toBeInTheDocument();
  });
  it("keep rows stay plain", () => {
    renderRow(keepActive);
    expect(screen.queryByText(/NOTICE:/)).not.toBeInTheDocument();
    expect(screen.getByText(/active, 3 apps/)).toBeInTheDocument();
  });
  it("plain mode drops the register but keeps the facts", () => {
    renderRow(reclaimNever, true);
    expect(screen.queryByText(/NOTICE:/)).not.toBeInTheDocument();
    expect(screen.getByText(/never used Copilot/)).toBeInTheDocument();
  });
  it("renders the exact saving figure", () => {
    renderRow(reclaimNever);
    expect(screen.getByTestId("row-saving")).toHaveTextContent("+$30");
  });
});

describe("EvidencePanel — register-free by construction", () => {
  it("states raw facts, never the Committee register", () => {
    render(<EvidencePanel seat={reclaimNever} />);
    expect(screen.getByTestId("evidence-activity")).toHaveTextContent(
      "no activity on record (vendor retains 90 days)",
    );
    expect(document.body.textContent).not.toContain("NOTICE");
    expect(document.body.textContent).not.toContain("committee");
  });
});

describe("ClientTile — derived stage, true savings", () => {
  it("renders stage and sealed savings exactly", () => {
    render(
      <ClientTile
        client={{ name: "Tailspin", stage: "sealed", sealedSavingsUsd: 270 }}
      />,
    );
    expect(screen.getByText("Tailspin")).toBeInTheDocument();
    expect(screen.getByTestId("tile-savings")).toHaveTextContent("$270");
  });
  it("shows cases remaining only in review", () => {
    render(
      <ClientTile
        client={{ name: "Contoso", stage: "in-review", casesRemaining: 6 }}
      />,
    );
    expect(screen.getByText(/6 left/)).toBeInTheDocument();
  });
});

describe("ProductBadge / CaveatBlock", () => {
  it("badge is accessible with the full product name", () => {
    render(<ProductBadge product="m365" />);
    expect(screen.getByRole("img", { name: "Microsoft 365 Copilot" })).toBeInTheDocument();
  });
  it("caveats render verbatim and the block hides only when empty", () => {
    const { rerender } = render(<CaveatBlock caveats={["no message content is accessed"]} />);
    expect(screen.getByText("no message content is accessed")).toBeInTheDocument();
    rerender(<CaveatBlock caveats={[]} />);
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
  });
});

describe("VerdictStamp — deterministic physics", () => {
  it("same seed, same tilt; different seeds can differ", async () => {
    const { VerdictStamp } = await import("./VerdictStamp");
    const tiltOf = (seed: string) => {
      const { container, unmount } = render(
        <VerdictStamp verdict="reclaim" seed={seed} />,
      );
      const t = (container.firstChild as HTMLElement).style.getPropertyValue("--stamp-tilt");
      unmount();
      return t;
    };
    expect(tiltOf("m.ruiz")).toBe(tiltOf("m.ruiz"));
    const tilts = new Set(["a", "b", "c", "d", "e"].map(tiltOf));
    expect(tilts.size).toBeGreaterThan(1);
  });
});

describe("projectedSavings mirrors advisory arithmetic", () => {
  it("sums per-seat savings exactly", () => {
    expect(projectedSavings([reclaimNever, keepActive])).toBe(30);
  });
});
