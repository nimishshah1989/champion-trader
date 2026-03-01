"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import {
  getTrades,
  getTradeStats,
  createTrade,
  recordPartialExit,
  closeTrade,
  type Trade,
  type TradeStats,
  type TradeCreateRequest,
} from "@/lib/api";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import { InfoBanner, Term } from "@/components/info-banner";

// ---------------------------------------------------------------------------
// Constants & Helpers
// ---------------------------------------------------------------------------

const formatINR = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 2,
});

const formatINRCompact = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

const DEFAULT_ACCOUNT_VALUE = 500000;

type StatusFilter = "ALL" | "OPEN" | "PARTIAL" | "CLOSED";

const STATUS_FILTERS: StatusFilter[] = ["ALL", "OPEN", "PARTIAL", "CLOSED"];

const ENTRY_TYPES = ["LIVE_BREAK", "CLOSE_ABOVE", "NEXT_DAY_HIGH"] as const;

const EXIT_REASONS_PARTIAL = ["2R", "NE", "GE", "EE", "EARNINGS_RISK", "MANUAL"] as const;

const EXIT_REASONS_CLOSE = ["SL", "FINAL_50DMA", "FINAL_20DMA", "EARNINGS", "MANUAL"] as const;

const MARKET_STANCES = ["STRONG", "MODERATE", "WEAK"] as const;

const SETUP_TYPES = ["PPC", "NPC", "CONTRACTION", "POWER_PLAY", "OTHER"] as const;

function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "2-digit",
    });
  } catch {
    return dateStr;
  }
}

function todayISO(): string {
  return new Date().toISOString().split("T")[0];
}

// ---------------------------------------------------------------------------
// Skeleton Loaders
// ---------------------------------------------------------------------------

function StatsSkeletons() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="bg-white rounded-xl border border-slate-200 p-5">
          <Skeleton className="h-4 w-20 bg-slate-100 mb-2" />
          <Skeleton className="h-8 w-16 bg-slate-100" />
        </div>
      ))}
    </div>
  );
}

function TableSkeletons() {
  return (
    <div className="space-y-1">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="flex items-center gap-4 px-5 py-3">
          <Skeleton className="h-5 w-24 bg-slate-100" />
          <Skeleton className="h-5 w-20 bg-slate-100" />
          <Skeleton className="h-5 w-16 bg-slate-100" />
          <Skeleton className="h-5 w-12 bg-slate-100" />
          <Skeleton className="h-5 w-12 bg-slate-100" />
          <Skeleton className="h-5 w-16 bg-slate-100" />
          <Skeleton className="h-5 w-20 bg-slate-100" />
          <Skeleton className="h-5 w-14 bg-slate-100" />
          <Skeleton className="h-5 w-16 bg-slate-100 rounded-full" />
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Stat Cards
// ---------------------------------------------------------------------------

function StatCards({
  stats,
  loading,
}: {
  stats: TradeStats | null;
  loading: boolean;
}) {
  if (loading) return <StatsSkeletons />;

  const totalTrades = stats?.total_trades ?? 0;
  const winRate = stats?.win_rate;
  const arr = stats?.arr;
  const totalPnl = stats?.total_pnl ?? 0;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {/* Total Trades */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">
          Total Trades
        </p>
        <span className="text-3xl font-bold text-slate-800 font-mono tabular-nums">
          {totalTrades}
        </span>
        <p className="text-[10px] text-slate-400 mt-1">
          {stats ? `${stats.open_trades} open, ${stats.closed_trades} closed` : "No data"}
        </p>
      </div>

      {/* Win Rate */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">
          Win Rate
        </p>
        {winRate != null ? (
          <span
            className={`text-3xl font-bold font-mono tabular-nums ${
              winRate >= 40 ? "text-emerald-600" : "text-red-600"
            }`}
          >
            {winRate.toFixed(1)}%
          </span>
        ) : (
          <span className="text-3xl font-bold text-slate-300">--</span>
        )}
        <p className="text-[10px] text-slate-400 mt-1">
          {stats ? `${stats.win_count}W / ${stats.loss_count}L` : "No closed trades"}
        </p>
      </div>

      {/* ARR */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">
          Avg Reward:Risk
        </p>
        {arr != null ? (
          <span
            className={`text-3xl font-bold font-mono tabular-nums ${
              arr >= 2 ? "text-emerald-600" : "text-red-600"
            }`}
          >
            {arr.toFixed(2)}
          </span>
        ) : (
          <span className="text-3xl font-bold text-slate-300">--</span>
        )}
        <p className="text-[10px] text-slate-400 mt-1">Target: 2.0+</p>
      </div>

      {/* Total P&L */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">
          Total P&L
        </p>
        <span
          className={`text-2xl font-bold font-mono tabular-nums ${
            totalPnl >= 0 ? "text-emerald-600" : "text-red-600"
          }`}
        >
          {totalPnl !== 0 ? formatINRCompact.format(totalPnl) : "--"}
        </span>
        <p className="text-[10px] text-slate-400 mt-1">Gross realized P&L</p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Status Badge
// ---------------------------------------------------------------------------

function StatusBadge({ status, pnl }: { status: string; pnl: number | null }) {
  let colorClasses = "bg-blue-50 text-blue-700 border-blue-200";

  if (status === "PARTIAL") {
    colorClasses = "bg-amber-50 text-amber-700 border-amber-200";
  } else if (status === "CLOSED") {
    colorClasses =
      pnl != null && pnl >= 0
        ? "bg-emerald-50 text-emerald-700 border-emerald-200"
        : "bg-red-50 text-red-700 border-red-200";
  }

  return (
    <span
      className={`${colorClasses} border rounded-full px-2 py-0.5 text-[10px] font-semibold`}
    >
      {status}
    </span>
  );
}

// ---------------------------------------------------------------------------
// New Trade Form
// ---------------------------------------------------------------------------

interface TradeFormData {
  symbol: string;
  entry_date: string;
  entry_type: string;
  entry_price_half1: string;
  qty_half1: string;
  entry_price_half2: string;
  qty_half2: string;
  trp_pct: string;
  setup_type: string;
  market_stance: string;
  notes: string;
}

const EMPTY_TRADE_FORM: TradeFormData = {
  symbol: "",
  entry_date: todayISO(),
  entry_type: "LIVE_BREAK",
  entry_price_half1: "",
  qty_half1: "",
  entry_price_half2: "",
  qty_half2: "",
  trp_pct: "",
  setup_type: "",
  market_stance: "",
  notes: "",
};

function NewTradeForm({
  onSave,
  onCancel,
}: {
  onSave: (data: TradeCreateRequest) => Promise<void>;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<TradeFormData>(EMPTY_TRADE_FORM);
  const [submitting, setSubmitting] = useState(false);

  function updateField<K extends keyof TradeFormData>(key: K, value: TradeFormData[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  // Auto-calculated values
  const calculations = useMemo(() => {
    const priceH1 = parseFloat(form.entry_price_half1) || 0;
    const qtyH1 = parseInt(form.qty_half1) || 0;
    const priceH2 = parseFloat(form.entry_price_half2) || 0;
    const qtyH2 = parseInt(form.qty_half2) || 0;
    const trpPct = parseFloat(form.trp_pct) || 0;

    const totalQty = qtyH1 + qtyH2;
    const avgEntryPrice =
      totalQty > 0 ? (priceH1 * qtyH1 + priceH2 * qtyH2) / totalQty : priceH1;

    const slPrice = avgEntryPrice > 0 && trpPct > 0 ? avgEntryPrice * (1 - trpPct / 100) : 0;
    const slPct = trpPct;
    const rptAmount = DEFAULT_ACCOUNT_VALUE * (0.5 / 100); // 0.5% default RPT

    // Target levels based on R multiples
    const riskPerShare = avgEntryPrice - slPrice;
    const target2r = riskPerShare > 0 ? avgEntryPrice + 2 * riskPerShare : 0;
    const targetNE = riskPerShare > 0 ? avgEntryPrice + 3 * riskPerShare : 0;
    const targetGE = riskPerShare > 0 ? avgEntryPrice + 5 * riskPerShare : 0;
    const targetEE = riskPerShare > 0 ? avgEntryPrice + 8 * riskPerShare : 0;

    return {
      totalQty,
      avgEntryPrice,
      slPrice,
      slPct,
      rptAmount,
      target2r,
      targetNE,
      targetGE,
      targetEE,
    };
  }, [form.entry_price_half1, form.qty_half1, form.entry_price_half2, form.qty_half2, form.trp_pct]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    // Validation
    if (!form.symbol.trim()) {
      toast.error("Symbol is required");
      return;
    }
    if (!form.entry_price_half1 || parseFloat(form.entry_price_half1) <= 0) {
      toast.error("Entry price (Half 1) is required");
      return;
    }
    if (!form.qty_half1 || parseInt(form.qty_half1) <= 0) {
      toast.error("Quantity (Half 1) is required");
      return;
    }
    if (!form.trp_pct || parseFloat(form.trp_pct) <= 0) {
      toast.error("TRP% is required to calculate SL and targets");
      return;
    }
    if (calculations.totalQty <= 0) {
      toast.error("Total quantity must be positive");
      return;
    }

    setSubmitting(true);

    const payload: TradeCreateRequest = {
      symbol: form.symbol.trim().toUpperCase(),
      entry_date: form.entry_date,
      entry_type: form.entry_type || undefined,
      entry_price_half1: parseFloat(form.entry_price_half1),
      entry_price_half2: form.entry_price_half2 ? parseFloat(form.entry_price_half2) : undefined,
      qty_half1: parseInt(form.qty_half1),
      qty_half2: form.qty_half2 ? parseInt(form.qty_half2) : undefined,
      total_qty: calculations.totalQty,
      avg_entry_price: Math.round(calculations.avgEntryPrice * 100) / 100,
      trp_at_entry: parseFloat(form.trp_pct),
      sl_price: Math.round(calculations.slPrice * 100) / 100,
      sl_pct: Math.round(calculations.slPct * 100) / 100,
      rpt_amount: Math.round(calculations.rptAmount * 100) / 100,
      target_2r: calculations.target2r > 0 ? Math.round(calculations.target2r * 100) / 100 : undefined,
      target_ne: calculations.targetNE > 0 ? Math.round(calculations.targetNE * 100) / 100 : undefined,
      target_ge: calculations.targetGE > 0 ? Math.round(calculations.targetGE * 100) / 100 : undefined,
      target_ee: calculations.targetEE > 0 ? Math.round(calculations.targetEE * 100) / 100 : undefined,
      market_stance_at_entry: form.market_stance || undefined,
      setup_type: form.setup_type || undefined,
      entry_notes: form.notes || undefined,
    };

    try {
      await onSave(payload);
    } finally {
      setSubmitting(false);
    }
  }

  const inputClass =
    "w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none";
  const labelClass = "text-xs text-slate-500 mb-1 block font-medium";

  return (
    <div className="bg-white rounded-xl border border-slate-200 border-l-4 border-l-teal-500 p-5 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-800">Log New Trade</h3>
        <button
          onClick={onCancel}
          className="text-xs text-slate-400 hover:text-slate-600 transition-colors"
        >
          Cancel
        </button>
      </div>

      <form onSubmit={handleSubmit}>
        {/* Row 1: Core trade details */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 items-end">
          <div>
            <label className={labelClass}>Symbol *</label>
            <input
              type="text"
              placeholder="e.g. RELIANCE"
              className={inputClass}
              value={form.symbol}
              onChange={(e) => updateField("symbol", e.target.value.toUpperCase())}
              autoFocus
            />
          </div>
          <div>
            <label className={labelClass}>Entry Date</label>
            <input
              type="date"
              className={inputClass}
              value={form.entry_date}
              onChange={(e) => updateField("entry_date", e.target.value)}
            />
          </div>
          <div>
            <label className={labelClass}>Entry Type</label>
            <select
              className={inputClass}
              value={form.entry_type}
              onChange={(e) => updateField("entry_type", e.target.value)}
            >
              <option value="">Select</option>
              {ENTRY_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t.replace(/_/g, " ")}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelClass}>Price Half 1 *</label>
            <input
              type="number"
              step="0.05"
              placeholder="Entry price"
              className={inputClass}
              value={form.entry_price_half1}
              onChange={(e) => updateField("entry_price_half1", e.target.value)}
            />
          </div>
          <div>
            <label className={labelClass}>Qty Half 1 *</label>
            <input
              type="number"
              step="1"
              placeholder="Quantity"
              className={inputClass}
              value={form.qty_half1}
              onChange={(e) => updateField("qty_half1", e.target.value)}
            />
          </div>
          <div>
            <label className={labelClass}>TRP% *</label>
            <input
              type="number"
              step="0.1"
              placeholder="e.g. 7"
              className={inputClass}
              value={form.trp_pct}
              onChange={(e) => updateField("trp_pct", e.target.value)}
            />
          </div>
        </div>

        {/* Row 2: Optional half 2 and setup */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 items-end mt-4">
          <div>
            <label className={labelClass}>Price Half 2</label>
            <input
              type="number"
              step="0.05"
              placeholder="Optional"
              className={inputClass}
              value={form.entry_price_half2}
              onChange={(e) => updateField("entry_price_half2", e.target.value)}
            />
          </div>
          <div>
            <label className={labelClass}>Qty Half 2</label>
            <input
              type="number"
              step="1"
              placeholder="Optional"
              className={inputClass}
              value={form.qty_half2}
              onChange={(e) => updateField("qty_half2", e.target.value)}
            />
          </div>
          <div>
            <label className={labelClass}>Setup Type</label>
            <select
              className={inputClass}
              value={form.setup_type}
              onChange={(e) => updateField("setup_type", e.target.value)}
            >
              <option value="">Select</option>
              {SETUP_TYPES.map((s) => (
                <option key={s} value={s}>
                  {s.replace(/_/g, " ")}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelClass}>Market Stance</label>
            <select
              className={inputClass}
              value={form.market_stance}
              onChange={(e) => updateField("market_stance", e.target.value)}
            >
              <option value="">Select</option>
              {MARKET_STANCES.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>
          <div className="lg:col-span-2">
            <label className={labelClass}>Notes</label>
            <input
              type="text"
              placeholder="Entry observations..."
              className={inputClass}
              value={form.notes}
              onChange={(e) => updateField("notes", e.target.value)}
            />
          </div>
        </div>

        {/* Auto-calculated values display */}
        {calculations.avgEntryPrice > 0 && calculations.slPrice > 0 && (
          <div className="mt-4 p-3 bg-slate-50 rounded-lg border border-slate-100">
            <p className="text-[10px] text-slate-400 uppercase tracking-wider font-medium mb-2">
              Auto-Calculated
            </p>
            <div className="grid grid-cols-3 md:grid-cols-6 gap-4 text-xs">
              <div>
                <span className="text-slate-400">Total Qty</span>
                <p className="font-mono font-semibold text-slate-700">{calculations.totalQty}</p>
              </div>
              <div>
                <span className="text-slate-400">Avg Entry</span>
                <p className="font-mono font-semibold text-slate-700">
                  {formatINR.format(calculations.avgEntryPrice)}
                </p>
              </div>
              <div>
                <span className="text-slate-400">SL Price</span>
                <p className="font-mono font-semibold text-red-600">
                  {formatINR.format(calculations.slPrice)}
                </p>
              </div>
              <div>
                <span className="text-slate-400">Target 2R</span>
                <p className="font-mono font-semibold text-emerald-600">
                  {calculations.target2r > 0 ? formatINR.format(calculations.target2r) : "--"}
                </p>
              </div>
              <div>
                <span className="text-slate-400">Target NE</span>
                <p className="font-mono font-semibold text-emerald-600">
                  {calculations.targetNE > 0 ? formatINR.format(calculations.targetNE) : "--"}
                </p>
              </div>
              <div>
                <span className="text-slate-400">RPT Amount</span>
                <p className="font-mono font-semibold text-slate-700">
                  {formatINR.format(calculations.rptAmount)}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Submit row */}
        <div className="flex items-center justify-end gap-3 mt-4">
          <button
            type="button"
            onClick={onCancel}
            className="bg-white text-slate-600 font-medium px-4 py-2 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors text-sm"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting || !form.symbol.trim()}
            className="bg-teal-600 text-white font-medium px-6 py-2 rounded-lg hover:bg-teal-700 transition-colors text-sm disabled:opacity-50 flex items-center gap-1"
          >
            {submitting ? "Saving..." : "Log Trade"}
          </button>
        </div>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Partial Exit Modal
// ---------------------------------------------------------------------------

function PartialExitModal({
  trade,
  onSave,
  onClose,
}: {
  trade: Trade;
  onSave: (tradeId: number, data: { exit_date: string; exit_price: number; exit_qty: number; exit_reason: string; notes?: string }) => Promise<void>;
  onClose: () => void;
}) {
  const [exitDate, setExitDate] = useState(todayISO());
  const [exitPrice, setExitPrice] = useState("");
  const [exitQty, setExitQty] = useState("");
  const [exitReason, setExitReason] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const maxQty = trade.remaining_qty ?? trade.total_qty ?? 0;
  const entryPrice = trade.avg_entry_price ?? 0;
  const parsedPrice = parseFloat(exitPrice) || 0;
  const parsedQty = parseInt(exitQty) || 0;
  const estimatedPnl = parsedPrice > 0 && parsedQty > 0 ? (parsedPrice - entryPrice) * parsedQty : 0;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!exitPrice || parsedPrice <= 0) {
      toast.error("Exit price is required");
      return;
    }
    if (!exitQty || parsedQty <= 0) {
      toast.error("Exit quantity is required");
      return;
    }
    if (parsedQty > maxQty) {
      toast.error(`Exit qty cannot exceed remaining qty (${maxQty})`);
      return;
    }
    if (!exitReason) {
      toast.error("Exit reason is required");
      return;
    }

    setSubmitting(true);
    try {
      await onSave(trade.id, {
        exit_date: exitDate,
        exit_price: parsedPrice,
        exit_qty: parsedQty,
        exit_reason: exitReason,
        notes: notes || undefined,
      });
    } finally {
      setSubmitting(false);
    }
  }

  const inputClass =
    "w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none";
  const labelClass = "text-xs text-slate-500 mb-1 block font-medium";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="bg-white rounded-xl border border-slate-200 shadow-lg w-full max-w-lg mx-4 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-slate-800">
            Partial Exit -- {trade.symbol}
          </h3>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 transition-colors text-lg leading-none"
          >
            x
          </button>
        </div>

        <p className="text-xs text-slate-400 mb-4">
          Entry: {formatINR.format(entryPrice)} | Remaining qty: {maxQty}
        </p>

        <form onSubmit={handleSubmit}>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>Exit Date</label>
              <input
                type="date"
                className={inputClass}
                value={exitDate}
                onChange={(e) => setExitDate(e.target.value)}
              />
            </div>
            <div>
              <label className={labelClass}>Exit Price *</label>
              <input
                type="number"
                step="0.05"
                placeholder="Exit price"
                className={inputClass}
                value={exitPrice}
                onChange={(e) => setExitPrice(e.target.value)}
                autoFocus
              />
            </div>
            <div>
              <label className={labelClass}>Exit Qty * (max {maxQty})</label>
              <input
                type="number"
                step="1"
                min="1"
                max={maxQty}
                placeholder={`Max ${maxQty}`}
                className={inputClass}
                value={exitQty}
                onChange={(e) => setExitQty(e.target.value)}
              />
            </div>
            <div>
              <label className={labelClass}>Exit Reason *</label>
              <select
                className={inputClass}
                value={exitReason}
                onChange={(e) => setExitReason(e.target.value)}
              >
                <option value="">Select reason</option>
                {EXIT_REASONS_PARTIAL.map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="mt-4">
            <label className={labelClass}>Notes</label>
            <input
              type="text"
              placeholder="Optional notes..."
              className={inputClass}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>

          {/* Estimated P&L */}
          {estimatedPnl !== 0 && (
            <div className="mt-4 p-3 bg-slate-50 rounded-lg border border-slate-100 flex items-center justify-between">
              <span className="text-xs text-slate-400">Estimated P&L for this exit</span>
              <span
                className={`font-mono font-bold text-sm ${
                  estimatedPnl >= 0 ? "text-emerald-600" : "text-red-600"
                }`}
              >
                {estimatedPnl >= 0 ? "+" : ""}
                {formatINR.format(estimatedPnl)}
              </span>
            </div>
          )}

          <div className="flex items-center justify-end gap-3 mt-5">
            <button
              type="button"
              onClick={onClose}
              className="bg-white text-slate-600 font-medium px-4 py-2 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors text-sm"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="bg-teal-600 text-white font-medium px-6 py-2 rounded-lg hover:bg-teal-700 transition-colors text-sm disabled:opacity-50"
            >
              {submitting ? "Saving..." : "Record Exit"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Close Trade Modal
// ---------------------------------------------------------------------------

function CloseTradeModal({
  trade,
  onSave,
  onClose,
}: {
  trade: Trade;
  onSave: (tradeId: number, data: { exit_date: string; exit_price: number; exit_reason: string; exit_notes?: string }) => Promise<void>;
  onClose: () => void;
}) {
  const [exitDate, setExitDate] = useState(todayISO());
  const [exitPrice, setExitPrice] = useState("");
  const [exitReason, setExitReason] = useState("");
  const [exitNotes, setExitNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const entryPrice = trade.avg_entry_price ?? 0;
  const remainingQty = trade.remaining_qty ?? trade.total_qty ?? 0;
  const parsedPrice = parseFloat(exitPrice) || 0;
  const estimatedPnl = parsedPrice > 0 ? (parsedPrice - entryPrice) * remainingQty : 0;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!exitPrice || parsedPrice <= 0) {
      toast.error("Exit price is required");
      return;
    }
    if (!exitReason) {
      toast.error("Exit reason is required");
      return;
    }

    setSubmitting(true);
    try {
      await onSave(trade.id, {
        exit_date: exitDate,
        exit_price: parsedPrice,
        exit_reason: exitReason,
        exit_notes: exitNotes || undefined,
      });
    } finally {
      setSubmitting(false);
    }
  }

  const inputClass =
    "w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none";
  const labelClass = "text-xs text-slate-500 mb-1 block font-medium";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="bg-white rounded-xl border border-slate-200 shadow-lg w-full max-w-lg mx-4 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-slate-800">
            Close Trade -- {trade.symbol}
          </h3>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 transition-colors text-lg leading-none"
          >
            x
          </button>
        </div>

        <p className="text-xs text-slate-400 mb-4">
          Entry: {formatINR.format(entryPrice)} | Remaining qty: {remainingQty} | This will fully close the position.
        </p>

        <form onSubmit={handleSubmit}>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>Exit Date</label>
              <input
                type="date"
                className={inputClass}
                value={exitDate}
                onChange={(e) => setExitDate(e.target.value)}
              />
            </div>
            <div>
              <label className={labelClass}>Exit Price *</label>
              <input
                type="number"
                step="0.05"
                placeholder="Exit price"
                className={inputClass}
                value={exitPrice}
                onChange={(e) => setExitPrice(e.target.value)}
                autoFocus
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 mt-4">
            <div>
              <label className={labelClass}>Exit Reason *</label>
              <select
                className={inputClass}
                value={exitReason}
                onChange={(e) => setExitReason(e.target.value)}
              >
                <option value="">Select reason</option>
                {EXIT_REASONS_CLOSE.map((r) => (
                  <option key={r} value={r}>{r.replace(/_/g, " ")}</option>
                ))}
              </select>
            </div>
            <div>
              <label className={labelClass}>Notes</label>
              <input
                type="text"
                placeholder="Optional notes..."
                className={inputClass}
                value={exitNotes}
                onChange={(e) => setExitNotes(e.target.value)}
              />
            </div>
          </div>

          {/* Estimated P&L */}
          {estimatedPnl !== 0 && (
            <div className="mt-4 p-3 bg-slate-50 rounded-lg border border-slate-100 flex items-center justify-between">
              <span className="text-xs text-slate-400">Estimated gross P&L on close</span>
              <span
                className={`font-mono font-bold text-sm ${
                  estimatedPnl >= 0 ? "text-emerald-600" : "text-red-600"
                }`}
              >
                {estimatedPnl >= 0 ? "+" : ""}
                {formatINR.format(estimatedPnl)}
              </span>
            </div>
          )}

          <div className="flex items-center justify-end gap-3 mt-5">
            <button
              type="button"
              onClick={onClose}
              className="bg-white text-slate-600 font-medium px-4 py-2 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors text-sm"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="bg-red-600 text-white font-medium px-6 py-2 rounded-lg hover:bg-red-700 transition-colors text-sm disabled:opacity-50"
            >
              {submitting ? "Closing..." : "Close Trade"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Expandable Trade Detail Row
// ---------------------------------------------------------------------------

function TradeDetailRow({
  trade,
  onPartialExit,
  onCloseTrade,
}: {
  trade: Trade;
  onPartialExit: (trade: Trade) => void;
  onCloseTrade: (trade: Trade) => void;
}) {
  return (
    <tr>
      <td colSpan={9} className="px-5 py-4 bg-slate-50/80 border-b border-slate-100">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-x-8 gap-y-3 text-xs">
          {/* Column 1: Entry details */}
          <div className="space-y-2">
            <p className="text-[10px] text-slate-400 uppercase tracking-wider font-medium">
              Entry Details
            </p>
            <div className="space-y-1">
              <div className="flex justify-between">
                <span className="text-slate-400">Entry Type</span>
                <span className="font-medium text-slate-700">
                  {trade.entry_type ? trade.entry_type.replace(/_/g, " ") : "--"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Avg Entry</span>
                <span className="font-mono font-semibold text-slate-700">
                  {trade.avg_entry_price != null ? formatINR.format(trade.avg_entry_price) : "--"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Total Qty</span>
                <span className="font-mono font-semibold text-slate-700">
                  {trade.total_qty ?? "--"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Remaining</span>
                <span className="font-mono font-semibold text-slate-700">
                  {trade.remaining_qty ?? trade.total_qty ?? "--"}
                </span>
              </div>
            </div>
          </div>

          {/* Column 2: Risk levels */}
          <div className="space-y-2">
            <p className="text-[10px] text-slate-400 uppercase tracking-wider font-medium">
              Risk
            </p>
            <div className="space-y-1">
              <div className="flex justify-between">
                <span className="text-slate-400">SL Price</span>
                <span className="font-mono font-semibold text-red-600">
                  {trade.sl_price != null ? formatINR.format(trade.sl_price) : "--"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">SL %</span>
                <span className="font-mono font-semibold text-red-600">
                  {trade.sl_pct != null ? `${trade.sl_pct.toFixed(1)}%` : "--"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">RPT Amount</span>
                <span className="font-mono font-semibold text-slate-700">
                  {trade.rpt_amount != null ? formatINR.format(trade.rpt_amount) : "--"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Setup</span>
                <span className="font-medium text-slate-700">
                  {trade.setup_type ?? "--"}
                </span>
              </div>
            </div>
          </div>

          {/* Column 3: Targets */}
          <div className="space-y-2">
            <p className="text-[10px] text-slate-400 uppercase tracking-wider font-medium">
              Targets
            </p>
            <div className="space-y-1">
              <div className="flex justify-between">
                <span className="text-slate-400">2R Target</span>
                <span className="font-mono font-semibold text-emerald-600">
                  {trade.target_2r != null ? formatINR.format(trade.target_2r) : "--"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">NE Target</span>
                <span className="font-mono font-semibold text-emerald-600">
                  {trade.target_ne != null ? formatINR.format(trade.target_ne) : "--"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">GE Target</span>
                <span className="font-mono font-semibold text-emerald-600">
                  {trade.target_ge != null ? formatINR.format(trade.target_ge) : "--"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">EE Target</span>
                <span className="font-mono font-semibold text-emerald-600">
                  {trade.target_ee != null ? formatINR.format(trade.target_ee) : "--"}
                </span>
              </div>
            </div>
          </div>

          {/* Column 4: P&L and Actions */}
          <div className="space-y-2">
            <p className="text-[10px] text-slate-400 uppercase tracking-wider font-medium">
              P&L / Actions
            </p>
            <div className="space-y-1">
              <div className="flex justify-between">
                <span className="text-slate-400">Gross P&L</span>
                <span
                  className={`font-mono font-bold ${
                    trade.gross_pnl != null && trade.gross_pnl >= 0
                      ? "text-emerald-600"
                      : "text-red-600"
                  }`}
                >
                  {trade.gross_pnl != null ? formatINR.format(trade.gross_pnl) : "--"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">R-Multiple</span>
                <span
                  className={`font-mono font-bold ${
                    trade.r_multiple != null && trade.r_multiple >= 0
                      ? "text-emerald-600"
                      : "text-red-600"
                  }`}
                >
                  {trade.r_multiple != null ? `${trade.r_multiple.toFixed(2)}R` : "--"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">P&L %</span>
                <span
                  className={`font-mono font-bold ${
                    trade.pnl_pct != null && trade.pnl_pct >= 0
                      ? "text-emerald-600"
                      : "text-red-600"
                  }`}
                >
                  {trade.pnl_pct != null
                    ? `${trade.pnl_pct >= 0 ? "+" : ""}${trade.pnl_pct.toFixed(2)}%`
                    : "--"}
                </span>
              </div>
            </div>

            {/* Action buttons for OPEN/PARTIAL trades */}
            {(trade.status === "OPEN" || trade.status === "PARTIAL") && (
              <div className="flex flex-col gap-2 pt-2">
                <button
                  onClick={() => onPartialExit(trade)}
                  className="text-[11px] font-medium px-3 py-1.5 rounded border border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100 transition-colors text-center"
                >
                  Partial Exit
                </button>
                <button
                  onClick={() => onCloseTrade(trade)}
                  className="text-[11px] font-medium px-3 py-1.5 rounded border border-red-200 bg-red-50 text-red-600 hover:bg-red-100 transition-colors text-center"
                >
                  Close Trade
                </button>
              </div>
            )}

            {/* Closed trades show final status */}
            {trade.status === "CLOSED" && (
              <div className="pt-2">
                <div
                  className={`text-center py-2 rounded-lg text-[11px] font-bold ${
                    trade.gross_pnl != null && trade.gross_pnl >= 0
                      ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                      : "bg-red-50 text-red-700 border border-red-200"
                  }`}
                >
                  {trade.gross_pnl != null && trade.gross_pnl >= 0 ? "WIN" : "LOSS"} --{" "}
                  {trade.gross_pnl != null ? formatINR.format(trade.gross_pnl) : "--"}
                </div>
              </div>
            )}
          </div>
        </div>
      </td>
    </tr>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function TradesPage() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [stats, setStats] = useState<TradeStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<StatusFilter>("ALL");
  const [showNewTradeForm, setShowNewTradeForm] = useState(false);
  const [expandedTradeId, setExpandedTradeId] = useState<number | null>(null);
  const [partialExitTrade, setPartialExitTrade] = useState<Trade | null>(null);
  const [closeTradeTarget, setCloseTradeTarget] = useState<Trade | null>(null);

  // -----------------------------------------------------------------------
  // Data fetching
  // -----------------------------------------------------------------------

  const fetchData = useCallback(async () => {
    try {
      setError(null);
      const statusParam = activeFilter === "ALL" ? undefined : activeFilter;
      const [tradesData, statsData] = await Promise.allSettled([
        getTrades(statusParam),
        getTradeStats(),
      ]);

      if (tradesData.status === "fulfilled") {
        setTrades(tradesData.value);
      } else {
        throw tradesData.reason;
      }

      if (statsData.status === "fulfilled") {
        setStats(statsData.value);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to fetch trades";
      setError(message);
      toast.error("Failed to load trades");
    } finally {
      setLoading(false);
    }
  }, [activeFilter]);

  useEffect(() => {
    setLoading(true);
    fetchData();
  }, [fetchData]);

  // -----------------------------------------------------------------------
  // Handlers
  // -----------------------------------------------------------------------

  async function handleCreateTrade(data: TradeCreateRequest) {
    try {
      await createTrade(data);
      toast.success(`Trade logged: ${data.symbol}`);
      setShowNewTradeForm(false);
      await fetchData();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to create trade";
      toast.error(message);
    }
  }

  async function handlePartialExit(
    tradeId: number,
    data: { exit_date: string; exit_price: number; exit_qty: number; exit_reason: string; notes?: string },
  ) {
    try {
      const result = await recordPartialExit(tradeId, data);
      toast.success(`Partial exit recorded. Remaining qty: ${result.remaining_qty}`);
      setPartialExitTrade(null);
      await fetchData();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to record partial exit";
      toast.error(message);
    }
  }

  async function handleCloseTrade(
    tradeId: number,
    data: { exit_date: string; exit_price: number; exit_reason: string; exit_notes?: string },
  ) {
    try {
      const result = await closeTrade(tradeId, data);
      toast.success(`Trade closed. Gross P&L: ${formatINR.format(result.gross_pnl)}`);
      setCloseTradeTarget(null);
      setExpandedTradeId(null);
      await fetchData();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to close trade";
      toast.error(message);
    }
  }

  function toggleRow(tradeId: number) {
    setExpandedTradeId((prev) => (prev === tradeId ? null : tradeId));
  }

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-800 flex items-center gap-2">
            Trade Log
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Full trade history with P&L tracking and R-multiples
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-400 font-mono tabular-nums">
            {trades.length} trade{trades.length !== 1 ? "s" : ""}
          </span>
          {!showNewTradeForm && (
            <button
              onClick={() => setShowNewTradeForm(true)}
              className="bg-teal-600 text-white font-medium px-4 py-2 rounded-lg hover:bg-teal-700 transition-colors text-sm flex items-center gap-1"
            >
              <span>+</span> New Trade
            </button>
          )}
        </div>
      </div>

      <InfoBanner title="Quick Reference — Trade Terms" storageKey="trades">
        <Term label="Entry Types">LIVE_BREAK (buy on breakout bar), CLOSE_ABOVE (buy after close confirms above trigger), NEXT_DAY_HIGH (buy next day above high of breakout bar).</Term>
        <Term label="R-Multiple">P&L as multiples of initial risk. +2R = made 2x what you risked. -1R = full stop-loss hit.</Term>
        <Term label="Exit Framework">2R = book 20%, NE (4x TRP) = book 20%, GE (8x TRP) = book 40%, EE (12x TRP) = book 80%. Remaining rides with trailing SL.</Term>
        <Term label="ARR">Average Risk-Reward across all closed trades. Target &gt;2.0.</Term>
        <Term label="Status">OPEN (active), PARTIAL (some exits taken), CLOSED (fully exited).</Term>
      </InfoBanner>

      {/* New Trade Form (slide-down) */}
      {showNewTradeForm && (
        <NewTradeForm
          onSave={handleCreateTrade}
          onCancel={() => setShowNewTradeForm(false)}
        />
      )}

      {/* Stats Cards */}
      <StatCards stats={stats} loading={loading} />

      {/* Error state */}
      {error && !loading && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <p className="text-sm text-red-600 font-medium mb-2">Failed to load trades</p>
          <p className="text-xs text-red-400 mb-3">{error}</p>
          <button
            onClick={() => {
              setLoading(true);
              fetchData();
            }}
            className="bg-red-600 text-white text-xs font-medium px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Status filter tabs + Trade table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        {/* Filter Tabs */}
        <div className="px-5 py-3 border-b border-slate-100 flex items-center gap-2">
          {STATUS_FILTERS.map((filter) => (
            <button
              key={filter}
              onClick={() => setActiveFilter(filter)}
              className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                activeFilter === filter
                  ? "bg-teal-600 text-white"
                  : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
              }`}
            >
              {filter}
            </button>
          ))}
        </div>

        {/* Loading state */}
        {loading && <TableSkeletons />}

        {/* Empty state */}
        {!loading && !error && trades.length === 0 && (
          <div className="p-12 text-center">
            <p className="text-sm text-slate-400 mb-2">
              {activeFilter === "ALL"
                ? "No trades recorded yet."
                : `No ${activeFilter} trades found.`}
            </p>
            {activeFilter === "ALL" && (
              <button
                onClick={() => setShowNewTradeForm(true)}
                className="text-xs text-teal-600 hover:text-teal-700 font-medium mt-1"
              >
                Log your first trade
              </button>
            )}
          </div>
        )}

        {/* Trade table */}
        {!loading && !error && trades.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] text-slate-400 uppercase tracking-wider border-b border-slate-100">
                  <th className="px-5 py-2.5 font-medium">Symbol</th>
                  <th className="px-5 py-2.5 font-medium">Entry Date</th>
                  <th className="px-5 py-2.5 font-medium text-right">Entry Price</th>
                  <th className="px-5 py-2.5 font-medium text-right">Qty</th>
                  <th className="px-5 py-2.5 font-medium text-right">Remaining</th>
                  <th className="px-5 py-2.5 font-medium text-right">SL Price</th>
                  <th className="px-5 py-2.5 font-medium text-right">P&L</th>
                  <th className="px-5 py-2.5 font-medium text-right">R-Multiple</th>
                  <th className="px-5 py-2.5 font-medium text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((trade) => {
                  const isExpanded = expandedTradeId === trade.id;
                  return (
                    <TradeRow
                      key={trade.id}
                      trade={trade}
                      isExpanded={isExpanded}
                      onToggle={() => toggleRow(trade.id)}
                      onPartialExit={() => setPartialExitTrade(trade)}
                      onCloseTrade={() => setCloseTradeTarget(trade)}
                    />
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Partial Exit Modal */}
      {partialExitTrade && (
        <PartialExitModal
          trade={partialExitTrade}
          onSave={handlePartialExit}
          onClose={() => setPartialExitTrade(null)}
        />
      )}

      {/* Close Trade Modal */}
      {closeTradeTarget && (
        <CloseTradeModal
          trade={closeTradeTarget}
          onSave={handleCloseTrade}
          onClose={() => setCloseTradeTarget(null)}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Trade Table Row (extracted for expand/collapse logic)
// ---------------------------------------------------------------------------

function TradeRow({
  trade,
  isExpanded,
  onToggle,
  onPartialExit,
  onCloseTrade,
}: {
  trade: Trade;
  isExpanded: boolean;
  onToggle: () => void;
  onPartialExit: () => void;
  onCloseTrade: () => void;
}) {
  return (
    <>
      <tr
        onClick={onToggle}
        className={`border-b border-slate-50 hover:bg-slate-50/50 cursor-pointer transition-colors ${
          isExpanded ? "bg-slate-50/50" : ""
        }`}
      >
        {/* Symbol */}
        <td className="px-5 py-2.5 font-bold text-slate-800">
          <div className="flex items-center gap-1.5">
            <span
              className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                trade.status === "OPEN"
                  ? "bg-blue-500"
                  : trade.status === "PARTIAL"
                  ? "bg-amber-500"
                  : trade.gross_pnl != null && trade.gross_pnl >= 0
                  ? "bg-emerald-500"
                  : "bg-red-500"
              }`}
            />
            {trade.symbol}
          </div>
        </td>

        {/* Entry Date */}
        <td className="px-5 py-2.5 text-slate-500 text-xs">
          {formatDate(trade.entry_date)}
        </td>

        {/* Entry Price */}
        <td className="px-5 py-2.5 text-right font-mono tabular-nums text-xs text-slate-700">
          {trade.avg_entry_price != null ? formatINR.format(trade.avg_entry_price) : "--"}
        </td>

        {/* Qty */}
        <td className="px-5 py-2.5 text-right font-mono tabular-nums text-xs text-slate-700">
          {trade.total_qty ?? "--"}
        </td>

        {/* Remaining */}
        <td className="px-5 py-2.5 text-right font-mono tabular-nums text-xs text-slate-700">
          {trade.remaining_qty ?? trade.total_qty ?? "--"}
        </td>

        {/* SL Price */}
        <td className="px-5 py-2.5 text-right font-mono tabular-nums text-xs text-red-600 font-semibold">
          {trade.sl_price != null ? formatINR.format(trade.sl_price) : "--"}
        </td>

        {/* P&L */}
        <td className="px-5 py-2.5 text-right">
          {trade.gross_pnl != null ? (
            <span
              className={`font-mono tabular-nums text-xs font-semibold ${
                trade.gross_pnl >= 0 ? "text-emerald-600" : "text-red-600"
              }`}
            >
              {trade.gross_pnl >= 0 ? "+" : ""}
              {formatINR.format(trade.gross_pnl)}
            </span>
          ) : (
            <span className="text-xs text-slate-300">--</span>
          )}
        </td>

        {/* R-Multiple */}
        <td className="px-5 py-2.5 text-right">
          {trade.r_multiple != null ? (
            <span
              className={`font-mono tabular-nums text-xs font-semibold ${
                trade.r_multiple >= 0 ? "text-emerald-600" : "text-red-600"
              }`}
            >
              {trade.r_multiple >= 0 ? "+" : ""}
              {trade.r_multiple.toFixed(2)}R
            </span>
          ) : (
            <span className="text-xs text-slate-300">--</span>
          )}
        </td>

        {/* Status */}
        <td className="px-5 py-2.5 text-center">
          <StatusBadge status={trade.status} pnl={trade.gross_pnl} />
        </td>
      </tr>

      {/* Expanded detail row */}
      {isExpanded && (
        <TradeDetailRow
          trade={trade}
          onPartialExit={onPartialExit}
          onCloseTrade={onCloseTrade}
        />
      )}
    </>
  );
}
