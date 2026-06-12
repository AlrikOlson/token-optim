import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { QBRPack } from "./QBRPack";

const sealed = (period: string, savingsUsd: number) => ({
  period,
  savingsUsd,
  sealed: true,
});

describe("QBRPack — sealed-only invariant is mechanical", () => {
  it("throws on any unsealed period, naming it", () => {
    expect(() =>
      render(
        <QBRPack
          clientName="Contoso"
          quarter="Q2 2026"
          snapshots={[sealed("2026-04", 120), { period: "2026-05", savingsUsd: 1, sealed: false }]}
        />,
      ),
    ).toThrow(/sealed snapshots only.*2026-05/);
  });

  it("renders the exact quarter total from sealed months", () => {
    render(
      <QBRPack
        clientName="Contoso"
        quarter="Q2 2026"
        snapshots={[sealed("2026-04", 120), sealed("2026-05", 150)]}
      />,
    );
    expect(screen.getByTestId("qbr-total")).toHaveTextContent("$270");
  });
});
