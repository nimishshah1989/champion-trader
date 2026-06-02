import { describe, it, expect } from "vitest";
import { mergeScanAndWatchlist, calculatePositionFields } from "../pipeline-types";
import type { ScanResult, WatchlistItem } from "@/lib/api";

function scan(over: Partial<ScanResult>): ScanResult {
  return {
    id: 1, scan_date: "2024-06-02", symbol: "TITAN", scan_type: "V2",
    close_price: 3600, volume: 1000, avg_volume_20d: null, volume_ratio: null,
    trp: null, avg_trp: 2.8, trp_ratio: null, candle_body_pct: null, close_position: null,
    stage: "S2", above_30w_ma: null, ma_trending_up: null, base_days: 30,
    has_min_20_bar_base: true, base_quality: null, adt: null, passes_liquidity_filter: true,
    wuc_type: null, watchlist_bucket: "READY", trigger_level: 3650, notes: null, ...over,
  };
}

function watch(over: Partial<WatchlistItem>): WatchlistItem {
  return {
    id: 7, symbol: "TITAN", added_date: "2024-06-02", bucket: "READY", stage: "S2",
    base_days: 30, base_quality: null, wuc_types: null, trigger_level: 3650,
    planned_entry_price: 3650, planned_sl_pct: 2.8, planned_position_size: null,
    planned_half_qty: null, status: "ACTIVE", notes: null, ...over,
  };
}

describe("calculatePositionFields", () => {
  it("sizes from account x rpt / (entry x trp) and halves it", () => {
    // 500000 x 0.5% = 2500 risk; 601 x 3.18% = 19.1118/share -> floor(130.8) = 130, half 65
    expect(calculatePositionFields(500000, 0.5, 601, 3.18)).toEqual({ positionSize: 130, halfQty: 65 });
  });
  it("returns nulls when entry or trp is missing/zero", () => {
    expect(calculatePositionFields(500000, 0.5, null, 3.18)).toEqual({ positionSize: null, halfQty: null });
    expect(calculatePositionFields(500000, 0.5, 601, 0)).toEqual({ positionSize: null, halfQty: null });
  });
});

describe("mergeScanAndWatchlist", () => {
  it("maps the v2 avg_trp into the card TRP (not the null legacy trp) and sizes off it", () => {
    const cards = mergeScanAndWatchlist(
      [scan({ symbol: "TITAN", avg_trp: 2.8, trp: null })],
      [], 500000, 0.35,
    );
    expect(cards).toHaveLength(1);
    expect(cards[0].trp).toBe(2.8);          // avg_trp, not the null legacy trp
    expect(cards[0].scanType).toBe("V2");
    expect(cards[0].bucket).toBe("READY");
    expect(cards[0].positionSize).toBeGreaterThan(0); // sizing worked off avg_trp
  });

  it("still honours a legacy trp when avg_trp is absent", () => {
    const cards = mergeScanAndWatchlist(
      [scan({ symbol: "OLD", avg_trp: null, trp: 2.5 })],
      [], 500000, 0.35,
    );
    expect(cards[0].trp).toBe(2.5);
  });

  it("lets watchlist items take priority over a scan row for the same symbol", () => {
    const cards = mergeScanAndWatchlist(
      [scan({ symbol: "TITAN" })],
      [watch({ symbol: "TITAN", bucket: "NEAR" })],
      500000, 0.35,
    );
    expect(cards).toHaveLength(1);            // not duplicated
    expect(cards[0].watchlistId).not.toBeNull();
    expect(cards[0].bucket).toBe("NEAR");     // from the watchlist, not the scan
  });
});
