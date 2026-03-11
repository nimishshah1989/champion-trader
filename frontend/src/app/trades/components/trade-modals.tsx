"use client";

import { useState } from "react";
import type { Trade } from "@/lib/api";
import { toast } from "sonner";
import {
  formatINR,
  todayISO,
  EXIT_REASONS_PARTIAL,
  EXIT_REASONS_CLOSE,
  INPUT_CLASS,
  LABEL_CLASS,
} from "./trade-helpers";

// ---------------------------------------------------------------------------
// Partial Exit Modal
// ---------------------------------------------------------------------------

export function PartialExitModal({
  trade,
  onSave,
  onClose,
}: {
  trade: Trade;
  onSave: (
    tradeId: number,
    data: {
      exit_date: string;
      exit_price: number;
      exit_qty: number;
      exit_reason: string;
      notes?: string;
    },
  ) => Promise<void>;
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
  const estimatedPnl =
    parsedPrice > 0 && parsedQty > 0
      ? (parsedPrice - entryPrice) * parsedQty
      : 0;

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
              <label className={LABEL_CLASS}>Exit Date</label>
              <input
                type="date"
                className={INPUT_CLASS}
                value={exitDate}
                onChange={(e) => setExitDate(e.target.value)}
              />
            </div>
            <div>
              <label className={LABEL_CLASS}>Exit Price *</label>
              <input
                type="number"
                step="0.05"
                placeholder="Exit price"
                className={INPUT_CLASS}
                value={exitPrice}
                onChange={(e) => setExitPrice(e.target.value)}
                autoFocus
              />
            </div>
            <div>
              <label className={LABEL_CLASS}>Exit Qty * (max {maxQty})</label>
              <input
                type="number"
                step="1"
                min="1"
                max={maxQty}
                placeholder={`Max ${maxQty}`}
                className={INPUT_CLASS}
                value={exitQty}
                onChange={(e) => setExitQty(e.target.value)}
              />
            </div>
            <div>
              <label className={LABEL_CLASS}>Exit Reason *</label>
              <select
                className={INPUT_CLASS}
                value={exitReason}
                onChange={(e) => setExitReason(e.target.value)}
              >
                <option value="">Select reason</option>
                {EXIT_REASONS_PARTIAL.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="mt-4">
            <label className={LABEL_CLASS}>Notes</label>
            <input
              type="text"
              placeholder="Optional notes..."
              className={INPUT_CLASS}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>

          {/* Estimated P&L */}
          {estimatedPnl !== 0 && (
            <div className="mt-4 p-3 bg-slate-50 rounded-lg border border-slate-100 flex items-center justify-between">
              <span className="text-xs text-slate-400">
                Estimated P&L for this exit
              </span>
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

export function CloseTradeModal({
  trade,
  onSave,
  onClose,
}: {
  trade: Trade;
  onSave: (
    tradeId: number,
    data: {
      exit_date: string;
      exit_price: number;
      exit_reason: string;
      exit_notes?: string;
    },
  ) => Promise<void>;
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
  const estimatedPnl =
    parsedPrice > 0 ? (parsedPrice - entryPrice) * remainingQty : 0;

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
          Entry: {formatINR.format(entryPrice)} | Remaining qty: {remainingQty} |
          This will fully close the position.
        </p>

        <form onSubmit={handleSubmit}>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={LABEL_CLASS}>Exit Date</label>
              <input
                type="date"
                className={INPUT_CLASS}
                value={exitDate}
                onChange={(e) => setExitDate(e.target.value)}
              />
            </div>
            <div>
              <label className={LABEL_CLASS}>Exit Price *</label>
              <input
                type="number"
                step="0.05"
                placeholder="Exit price"
                className={INPUT_CLASS}
                value={exitPrice}
                onChange={(e) => setExitPrice(e.target.value)}
                autoFocus
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 mt-4">
            <div>
              <label className={LABEL_CLASS}>Exit Reason *</label>
              <select
                className={INPUT_CLASS}
                value={exitReason}
                onChange={(e) => setExitReason(e.target.value)}
              >
                <option value="">Select reason</option>
                {EXIT_REASONS_CLOSE.map((r) => (
                  <option key={r} value={r}>
                    {r.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className={LABEL_CLASS}>Notes</label>
              <input
                type="text"
                placeholder="Optional notes..."
                className={INPUT_CLASS}
                value={exitNotes}
                onChange={(e) => setExitNotes(e.target.value)}
              />
            </div>
          </div>

          {/* Estimated P&L */}
          {estimatedPnl !== 0 && (
            <div className="mt-4 p-3 bg-slate-50 rounded-lg border border-slate-100 flex items-center justify-between">
              <span className="text-xs text-slate-400">
                Estimated gross P&L on close
              </span>
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
