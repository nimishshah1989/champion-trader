import { describe, it, expect } from "vitest";
import { effectiveStop, isTrailing, isV2Trade } from "../trade-helpers";
import type { Trade } from "@/lib/api";

function trade(over: Partial<Trade>): Trade {
  return {
    id: 1, symbol: "X", entry_date: "2024-01-01", entry_type: null,
    avg_entry_price: 100, total_qty: 10, sl_price: 95, sl_pct: 5, rpt_amount: 500,
    target_2r: null, target_ne: null, target_ge: null, target_ee: null,
    status: "OPEN", remaining_qty: 10, gross_pnl: null, r_multiple: null, pnl_pct: null,
    setup_type: null, current_stop: null, highest_high: null, atr_at_entry: null,
    signal_type: null, regime_at_entry: null, volume_ratio_at_entry: null,
    avg_trp_at_entry: null, strategy_version: null, ...over,
  };
}

describe("effectiveStop", () => {
  it("uses current_stop (the trailing chandelier) when present", () => {
    expect(effectiveStop(trade({ sl_price: 95, current_stop: 98 }))).toBe(98);
  });
  it("falls back to the initial sl_price when current_stop is null", () => {
    expect(effectiveStop(trade({ sl_price: 95, current_stop: null }))).toBe(95);
  });
  it("returns null when neither stop is set", () => {
    expect(effectiveStop(trade({ sl_price: null, current_stop: null }))).toBeNull();
  });
});

describe("isTrailing", () => {
  it("is true once current_stop ratchets above the initial 1R", () => {
    expect(isTrailing(trade({ sl_price: 95, current_stop: 98 }))).toBe(true);
  });
  it("is false when current_stop equals the initial SL (not yet ratcheted)", () => {
    expect(isTrailing(trade({ sl_price: 95, current_stop: 95 }))).toBe(false);
  });
  it("is false when there is no current_stop", () => {
    expect(isTrailing(trade({ sl_price: 95, current_stop: null }))).toBe(false);
  });
});

describe("isV2Trade", () => {
  it("is true when any v2 trail/attribution field is present", () => {
    expect(isV2Trade(trade({ current_stop: 98 }))).toBe(true);
    expect(isV2Trade(trade({ highest_high: 110 }))).toBe(true);
    expect(isV2Trade(trade({ atr_at_entry: 12 }))).toBe(true);
    expect(isV2Trade(trade({ signal_type: "S2" }))).toBe(true);
    expect(isV2Trade(trade({ avg_trp_at_entry: 3 }))).toBe(true);
  });
  it("is false for a legacy trade carrying only the R-ladder targets", () => {
    expect(isV2Trade(trade({ target_2r: 110, target_ne: 120, target_ge: 130 }))).toBe(false);
  });
});
