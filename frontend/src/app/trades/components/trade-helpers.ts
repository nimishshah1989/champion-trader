// ---------------------------------------------------------------------------
// Shared constants and helpers for the Trades feature
// ---------------------------------------------------------------------------

// Re-export shared formatters for backwards compatibility
export { formatINR, formatINRCompact, formatDateShort as formatDate, todayISO } from "@/lib/format";

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
