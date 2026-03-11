// ---------------------------------------------------------------------------
// Pipeline — Shared types and constants
// ---------------------------------------------------------------------------

import type { ScanResult, WatchlistItem } from "@/lib/api";

export type ScanType = "PPC" | "NPC" | "CONTRACTION" | "ALL";
export type Bucket = "READY" | "NEAR" | "AWAY";

/**
 * A unified card item that merges scan results with watchlist data.
 * When a stock exists in both, watchlist fields take precedence.
 */
export interface PipelineCard {
  /** Watchlist ID if persisted; null for scan-only items */
  watchlistId: number | null;
  symbol: string;
  bucket: Bucket;
  closePrice: number | null;
  trp: number | null;
  volumeRatio: number | null;
  baseDays: number | null;
  triggerLevel: number | null;
  stage: string | null;
  scanType: string | null;
  wucTypes: string | null;
  notes: string | null;
  addedDate: string | null;
  /** Position size calculated from settings context */
  positionSize: number | null;
  /** Half quantity for 50/50 entry split */
  halfQty: number | null;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const SCAN_TYPE_OPTIONS: { value: ScanType; label: string; fullName: string }[] = [
  { value: "ALL", label: "All Scans", fullName: "Positive Pivotal Candle + Negative Pivotal Candle + Base Contraction" },
  { value: "PPC", label: "Positive Pivotal Candle", fullName: "Positive Pivotal Candle" },
  { value: "NPC", label: "Negative Pivotal Candle", fullName: "Negative Pivotal Candle" },
  { value: "CONTRACTION", label: "Base Contraction", fullName: "Base Contraction" },
];

export const BUCKET_ORDER: Bucket[] = ["READY", "NEAR", "AWAY"];

export const BUCKET_META: Record<
  Bucket,
  {
    label: string;
    color: string;
    headerBg: string;
    borderColor: string;
    badgeBg: string;
    subtitle: string;
    emptyIcon: string;
    emptyText: string;
  }
> = {
  READY: {
    label: "READY",
    color: "text-emerald-700",
    headerBg: "bg-emerald-50",
    borderColor: "border-emerald-200",
    badgeBg: "bg-emerald-100 text-emerald-700",
    subtitle: "Trigger Set",
    emptyIcon: "target",
    emptyText: "No stocks ready for entry. Run a scan or promote from NEAR.",
  },
  NEAR: {
    label: "NEAR",
    color: "text-amber-700",
    headerBg: "bg-amber-50",
    borderColor: "border-amber-200",
    badgeBg: "bg-amber-100 text-amber-700",
    subtitle: "Watch Closely",
    emptyIcon: "eye",
    emptyText: "No stocks approaching readiness. Promote from AWAY as bases mature.",
  },
  AWAY: {
    label: "AWAY",
    color: "text-blue-700",
    headerBg: "bg-blue-50",
    borderColor: "border-blue-200",
    badgeBg: "bg-blue-100 text-blue-700",
    subtitle: "Building Base",
    emptyIcon: "radar",
    emptyText: "No stocks in early base stage. Run a scan to discover candidates.",
  },
};

export const STAGE_COLORS: Record<string, string> = {
  S1: "bg-slate-100 text-slate-600",
  S1B: "bg-teal-100 text-teal-700",
  S2: "bg-blue-100 text-blue-700",
  S3: "bg-amber-100 text-amber-700",
  S4: "bg-red-100 text-red-700",
  UNKNOWN: "bg-slate-100 text-slate-500",
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// Re-export shared formatters for pipeline components
export { formatINRValue as formatINR, todayISO as getTodayISO } from "@/lib/format";

/**
 * Calculate position size and half quantity from account value, RPT%, entry price, and TRP%.
 * Returns { positionSize, halfQty } or nulls if inputs are insufficient.
 */
export function calculatePositionFields(
  accountValue: number,
  rptPct: number,
  entryPrice: number | null,
  trpPct: number | null,
): { positionSize: number | null; halfQty: number | null } {
  if (!entryPrice || !trpPct || trpPct <= 0 || entryPrice <= 0) {
    return { positionSize: null, halfQty: null };
  }
  const rptAmount = accountValue * (rptPct / 100);
  const slDistance = entryPrice * (trpPct / 100);
  if (slDistance <= 0) return { positionSize: null, halfQty: null };
  const size = Math.floor(rptAmount / slDistance);
  return { positionSize: size, halfQty: Math.floor(size / 2) };
}

/**
 * Merge scan results and watchlist items into a single PipelineCard array.
 * Watchlist items take priority; scan results without a watchlist entry are added
 * using their `watchlist_bucket` field for categorization.
 */
export function mergeScanAndWatchlist(
  scanResults: ScanResult[],
  watchlistItems: WatchlistItem[],
  accountValue: number,
  rptPct: number,
): PipelineCard[] {
  const cards: PipelineCard[] = [];
  const watchlistSymbols = new Set(watchlistItems.map((w) => w.symbol));

  // Add watchlist items first
  for (const w of watchlistItems) {
    const entryPrice = w.trigger_level ?? w.planned_entry_price;
    const trpPct = w.planned_sl_pct;
    const { positionSize, halfQty } = calculatePositionFields(accountValue, rptPct, entryPrice, trpPct);

    cards.push({
      watchlistId: w.id,
      symbol: w.symbol,
      bucket: (w.bucket as Bucket) || "AWAY",
      closePrice: null,
      trp: trpPct,
      volumeRatio: null,
      baseDays: w.base_days,
      triggerLevel: w.trigger_level,
      stage: w.stage,
      scanType: null,
      wucTypes: w.wuc_types,
      notes: w.notes,
      addedDate: w.added_date,
      positionSize,
      halfQty,
    });
  }

  // Add scan results that are NOT already in the watchlist
  for (const s of scanResults) {
    if (watchlistSymbols.has(s.symbol)) continue;

    const entryPrice = s.trigger_level ?? s.close_price;
    const trpPct = s.trp;
    const { positionSize, halfQty } = calculatePositionFields(accountValue, rptPct, entryPrice, trpPct);

    cards.push({
      watchlistId: null,
      symbol: s.symbol,
      bucket: (s.watchlist_bucket as Bucket) || "AWAY",
      closePrice: s.close_price,
      trp: trpPct,
      volumeRatio: s.volume_ratio,
      baseDays: s.base_days,
      triggerLevel: s.trigger_level,
      stage: s.stage,
      scanType: s.scan_type,
      wucTypes: s.wuc_type,
      notes: s.notes,
      addedDate: null,
      positionSize,
      halfQty,
    });
  }

  return cards;
}
