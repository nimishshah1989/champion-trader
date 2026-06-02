import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/components/info-tooltip", () => ({ InfoTooltip: () => null }));

const { PipelineStockCard } = await import("../pipeline-stock-card");
import type { PipelineCard } from "../pipeline-types";

function card(over: Partial<PipelineCard>): PipelineCard {
  return {
    watchlistId: null, symbol: "TITAN", bucket: "READY", closePrice: 3600, trp: 2.8,
    volumeRatio: null, baseDays: 30, triggerLevel: 3650, stage: "S2", scanType: "V2",
    wucTypes: null, notes: null, addedDate: null, positionSize: 24, halfQty: 12, ...over,
  };
}

const noop = () => {};

describe("PipelineStockCard", () => {
  it("shows the V2 SETUP badge, the stage, and Avg TRP for a v2 scan card", () => {
    render(<PipelineStockCard card={card({})} onMove={noop} onRemove={noop} isUpdating={false} />);
    expect(screen.getByText("V2 SETUP")).toBeInTheDocument();
    expect(screen.getByText("S2")).toBeInTheDocument();
    expect(screen.getByText(/Avg TRP/)).toBeInTheDocument();
    expect(screen.getByText("2.80%")).toBeInTheDocument();
  });

  it("omits the scan-type badge for a watchlist-sourced card (scanType null)", () => {
    render(<PipelineStockCard card={card({ scanType: null })} onMove={noop} onRemove={noop} isUpdating={false} />);
    expect(screen.queryByText("V2 SETUP")).not.toBeInTheDocument();
    expect(screen.getByText("S2")).toBeInTheDocument(); // stage badge still present
  });
});
