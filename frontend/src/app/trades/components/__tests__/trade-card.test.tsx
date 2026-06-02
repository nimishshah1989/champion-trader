import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TradeRow } from "../trade-card";
import type { Trade } from "@/lib/api";

function trade(over: Partial<Trade>): Trade {
  return {
    id: 1, symbol: "X", entry_date: "2024-01-01", entry_type: "LIVE_BREAK",
    avg_entry_price: 601, total_qty: 131, sl_price: 581.9, sl_pct: 3.18, rpt_amount: 3500,
    target_2r: null, target_ne: null, target_ge: null, target_ee: null,
    status: "OPEN", remaining_qty: 131, gross_pnl: null, r_multiple: null, pnl_pct: null,
    setup_type: null, current_stop: null, highest_high: null, atr_at_entry: null,
    signal_type: null, regime_at_entry: null, volume_ratio_at_entry: null,
    avg_trp_at_entry: null, strategy_version: null, ...over,
  };
}

function renderRow(t: Trade) {
  return render(
    <table>
      <tbody>
        <TradeRow trade={t} isExpanded onToggle={() => {}} onPartialExit={() => {}} onCloseTrade={() => {}} />
      </tbody>
    </table>,
  );
}

describe("TradeRow — v2 trade", () => {
  it("shows the Stop & Trail block and the chandelier current stop", () => {
    renderRow(trade({
      symbol: "ASTERDM", sl_price: 581.9, current_stop: 595, highest_high: 648,
      atr_at_entry: 12.34, signal_type: "S2", regime_at_entry: "bull",
      volume_ratio_at_entry: 2.4, avg_trp_at_entry: 3.18, strategy_version: "v2",
    }));
    expect(screen.getByText("Stop & Trail")).toBeInTheDocument();
    expect(screen.getByText("Initial SL (1R)")).toBeInTheDocument();
    expect(screen.getByText("Highest High")).toBeInTheDocument();
  });

  it("shows the Attribution block (signal, regime, vol gate) — not the R-ladder", () => {
    renderRow(trade({
      symbol: "ASTERDM", current_stop: 595, signal_type: "S2", regime_at_entry: "bull",
      volume_ratio_at_entry: 2.4, avg_trp_at_entry: 3.18, strategy_version: "v2",
    }));
    expect(screen.getByText(/Attribution/)).toBeInTheDocument();
    expect(screen.getByText("Regime @ entry")).toBeInTheDocument();
    expect(screen.getByText("Vol ratio @ entry")).toBeInTheDocument();
    expect(screen.getAllByText("S2").length).toBeGreaterThanOrEqual(1); // badge + attribution row
    expect(screen.queryByText("2R Target")).not.toBeInTheDocument();
  });
});

describe("TradeRow — legacy trade", () => {
  it("falls back to the R-ladder targets when there is no v2 trail/attribution", () => {
    renderRow(trade({
      symbol: "OLD", current_stop: null, atr_at_entry: null, signal_type: null,
      avg_trp_at_entry: null, target_2r: 639.22, target_ne: 677.44, target_ge: 753.88,
    }));
    // Column 3 shows the legacy targets, not the v2 attribution block.
    expect(screen.getByText(/Targets/)).toBeInTheDocument();
    expect(screen.getByText("2R Target")).toBeInTheDocument();
    expect(screen.queryByText(/Attribution/)).not.toBeInTheDocument();
    expect(screen.queryByText("Regime @ entry")).not.toBeInTheDocument();
  });
});
