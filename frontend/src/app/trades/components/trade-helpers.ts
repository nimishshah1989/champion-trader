// ---------------------------------------------------------------------------
// Shared constants and helpers for the Trades feature
// ---------------------------------------------------------------------------

import type { Trade } from "@/lib/api";

// Re-export shared formatters for backwards compatibility
export { formatINR, formatINRCompact, formatDateShort as formatDate, todayISO } from "@/lib/format";

// ---------------------------------------------------------------------------
// v2 stop helpers — the validated stop is the chandelier trail (current_stop),
// which ratchets up from the initial 1R (sl_price). Fall back to sl_price for
// legacy trades or before the first ratchet.
// ---------------------------------------------------------------------------

export function effectiveStop(t: Trade): number | null {
  return t.current_stop ?? t.sl_price;
}

/** True once the chandelier has ratcheted the stop above the initial 1R. */
export function isTrailing(t: Trade): boolean {
  return t.current_stop != null && t.sl_price != null && t.current_stop > t.sl_price;
}

/** A v2 trade carries trail/attribution state; legacy trades carry the R-ladder targets. */
export function isV2Trade(t: Trade): boolean {
  return (
    t.current_stop != null ||
    t.highest_high != null ||
    t.atr_at_entry != null ||
    t.signal_type != null ||
    t.avg_trp_at_entry != null
  );
}

export type StatusFilter = "ALL" | "OPEN" | "PARTIAL" | "CLOSED";

export const STATUS_FILTERS: StatusFilter[] = ["ALL", "OPEN", "PARTIAL", "CLOSED"];

export const ENTRY_TYPES = ["LIVE_BREAK", "CLOSE_ABOVE", "NEXT_DAY_HIGH"] as const;

export const EXIT_REASONS_PARTIAL = [
  "2R",
  "NE",
  "GE",
  "EE",
  "EARNINGS_RISK",
  "MANUAL",
] as const;

export const EXIT_REASONS_CLOSE = [
  "SL",
  "FINAL_50DMA",
  "FINAL_20DMA",
  "EARNINGS",
  "MANUAL",
] as const;

export const MARKET_STANCES = ["STRONG", "MODERATE", "WEAK"] as const;

export const SETUP_TYPES = ["PPC", "NPC", "CONTRACTION", "POWER_PLAY", "OTHER"] as const;


export const INPUT_CLASS =
  "w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none";

export const LABEL_CLASS = "text-xs text-slate-500 mb-1 block font-medium";
