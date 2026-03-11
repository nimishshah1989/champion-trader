"use client";

import { useState, useMemo } from "react";
import type { TradeCreateRequest } from "@/lib/api";
import { toast } from "sonner";
import { useSettings } from "@/contexts/settings-context";
import { formatINR } from "@/lib/format";
import {
  todayISO,
  ENTRY_TYPES,
  SETUP_TYPES,
  MARKET_STANCES,
  INPUT_CLASS,
  LABEL_CLASS,
} from "./trade-helpers";

// ---------------------------------------------------------------------------
// Form Data Type
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

export function NewTradeForm({
  onSave,
  onCancel,
}: {
  onSave: (data: TradeCreateRequest) => Promise<void>;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<TradeFormData>(EMPTY_TRADE_FORM);
  const [submitting, setSubmitting] = useState(false);
  const { settings, effectiveRpt } = useSettings();

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

    const slPrice =
      avgEntryPrice > 0 && trpPct > 0
        ? avgEntryPrice * (1 - trpPct / 100)
        : 0;
    const slPct = trpPct;
    const rptAmount = settings.accountValue * (effectiveRpt / 100);

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
  }, [
    form.entry_price_half1,
    form.qty_half1,
    form.entry_price_half2,
    form.qty_half2,
    form.trp_pct,
    settings.accountValue,
    effectiveRpt,
  ]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

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
      toast.error("TRP% is required to calculate Stop Loss and targets");
      return;
    }
    if (calculations.totalQty <= 0) {
      toast.error("Total quantity must be positive");
      return;
    }

    setSubmitting(true);

    const roundTwo = (n: number) => Math.round(n * 100) / 100;

    const payload: TradeCreateRequest = {
      symbol: form.symbol.trim().toUpperCase(),
      entry_date: form.entry_date,
      entry_type: form.entry_type || undefined,
      entry_price_half1: parseFloat(form.entry_price_half1),
      entry_price_half2: form.entry_price_half2
        ? parseFloat(form.entry_price_half2)
        : undefined,
      qty_half1: parseInt(form.qty_half1),
      qty_half2: form.qty_half2 ? parseInt(form.qty_half2) : undefined,
      total_qty: calculations.totalQty,
      avg_entry_price: roundTwo(calculations.avgEntryPrice),
      trp_at_entry: parseFloat(form.trp_pct),
      sl_price: roundTwo(calculations.slPrice),
      sl_pct: roundTwo(calculations.slPct),
      rpt_amount: roundTwo(calculations.rptAmount),
      target_2r:
        calculations.target2r > 0 ? roundTwo(calculations.target2r) : undefined,
      target_ne:
        calculations.targetNE > 0 ? roundTwo(calculations.targetNE) : undefined,
      target_ge:
        calculations.targetGE > 0 ? roundTwo(calculations.targetGE) : undefined,
      target_ee:
        calculations.targetEE > 0 ? roundTwo(calculations.targetEE) : undefined,
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
            <label className={LABEL_CLASS}>Symbol *</label>
            <input
              type="text"
              placeholder="e.g. RELIANCE"
              className={INPUT_CLASS}
              value={form.symbol}
              onChange={(e) => updateField("symbol", e.target.value.toUpperCase())}
              autoFocus
            />
          </div>
          <div>
            <label className={LABEL_CLASS}>Entry Date</label>
            <input
              type="date"
              className={INPUT_CLASS}
              value={form.entry_date}
              onChange={(e) => updateField("entry_date", e.target.value)}
            />
          </div>
          <div>
            <label className={LABEL_CLASS}>Entry Type</label>
            <select
              className={INPUT_CLASS}
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
            <label className={LABEL_CLASS}>Price Half 1 *</label>
            <input
              type="number"
              step="0.05"
              placeholder="Entry price"
              className={INPUT_CLASS}
              value={form.entry_price_half1}
              onChange={(e) => updateField("entry_price_half1", e.target.value)}
            />
          </div>
          <div>
            <label className={LABEL_CLASS}>Qty Half 1 *</label>
            <input
              type="number"
              step="1"
              placeholder="Quantity"
              className={INPUT_CLASS}
              value={form.qty_half1}
              onChange={(e) => updateField("qty_half1", e.target.value)}
            />
          </div>
          <div>
            <label className={LABEL_CLASS}>TRP% *</label>
            <input
              type="number"
              step="0.1"
              placeholder="e.g. 7"
              className={INPUT_CLASS}
              value={form.trp_pct}
              onChange={(e) => updateField("trp_pct", e.target.value)}
            />
          </div>
        </div>

        {/* Row 2: Optional half 2 and setup */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 items-end mt-4">
          <div>
            <label className={LABEL_CLASS}>Price Half 2</label>
            <input
              type="number"
              step="0.05"
              placeholder="Optional"
              className={INPUT_CLASS}
              value={form.entry_price_half2}
              onChange={(e) => updateField("entry_price_half2", e.target.value)}
            />
          </div>
          <div>
            <label className={LABEL_CLASS}>Qty Half 2</label>
            <input
              type="number"
              step="1"
              placeholder="Optional"
              className={INPUT_CLASS}
              value={form.qty_half2}
              onChange={(e) => updateField("qty_half2", e.target.value)}
            />
          </div>
          <div>
            <label className={LABEL_CLASS}>Setup Type</label>
            <select
              className={INPUT_CLASS}
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
            <label className={LABEL_CLASS}>Market Stance</label>
            <select
              className={INPUT_CLASS}
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
            <label className={LABEL_CLASS}>Notes</label>
            <input
              type="text"
              placeholder="Entry observations..."
              className={INPUT_CLASS}
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
                <p className="font-mono font-semibold text-slate-700">
                  {calculations.totalQty}
                </p>
              </div>
              <div>
                <span className="text-slate-400">Avg Entry</span>
                <p className="font-mono font-semibold text-slate-700">
                  {formatINR.format(calculations.avgEntryPrice)}
                </p>
              </div>
              <div>
                <span className="text-slate-400">Stop Loss Price</span>
                <p className="font-mono font-semibold text-red-600">
                  {formatINR.format(calculations.slPrice)}
                </p>
              </div>
              <div>
                <span className="text-slate-400">Target 2R</span>
                <p className="font-mono font-semibold text-emerald-600">
                  {calculations.target2r > 0
                    ? formatINR.format(calculations.target2r)
                    : "--"}
                </p>
              </div>
              <div>
                <span className="text-slate-400">Target NE</span>
                <p className="font-mono font-semibold text-emerald-600">
                  {calculations.targetNE > 0
                    ? formatINR.format(calculations.targetNE)
                    : "--"}
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
