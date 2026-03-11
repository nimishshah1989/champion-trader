"use client";

import { type ActionAlert } from "@/lib/api";
import { InfoTooltip } from "@/components/info-tooltip";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

import { formatINR } from "@/lib/format";

/** Colors and styling for sell alert types */
const SELL_ALERT_STYLE: Record<string, { border: string; badge: string; badgeText: string }> = {
  SL_HIT: {
    border: "border-l-red-500",
    badge: "bg-red-600 text-white",
    badgeText: "STOP LOSS",
  },
  "2R_HIT": {
    border: "border-l-amber-500",
    badge: "bg-amber-500 text-white",
    badgeText: "2R TARGET",
  },
  NE_HIT: {
    border: "border-l-amber-500",
    badge: "bg-amber-500 text-white",
    badgeText: "NORMAL EXIT",
  },
  GE_HIT: {
    border: "border-l-teal-500",
    badge: "bg-teal-600 text-white",
    badgeText: "GREAT EXIT",
  },
  EE_HIT: {
    border: "border-l-emerald-500",
    badge: "bg-emerald-600 text-white",
    badgeText: "EXCELLENT EXIT",
  },
  FINAL_EXIT: {
    border: "border-l-slate-500",
    badge: "bg-slate-600 text-white",
    badgeText: "FINAL EXIT",
  },
};

// ---------------------------------------------------------------------------
// SellAlertCard
// ---------------------------------------------------------------------------

interface SellAlertCardProps {
  alert: ActionAlert;
  onAct: (id: number) => void;
  onDismiss: (id: number) => void;
  isActing: boolean;
}

export function SellAlertCard({ alert, onAct, onDismiss, isActing }: SellAlertCardProps) {
  const style = SELL_ALERT_STYLE[alert.alert_type] || {
    border: "border-l-slate-400",
    badge: "bg-slate-500 text-white",
    badgeText: alert.alert_type,
  };

  return (
    <div
      className={`bg-white rounded-xl border border-slate-200 border-l-4 ${style.border} p-5 hover:border-slate-300 transition-colors`}
    >
      {/* Header: Symbol + Type Badge */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-base font-bold text-slate-800 tracking-wide">
            {alert.symbol}
          </span>
          <span
            className={`${style.badge} rounded px-2 py-0.5 text-xs font-bold uppercase`}
          >
            {style.badgeText}
          </span>
        </div>
        {alert.trade_id !== null && (
          <span className="text-[10px] text-slate-400 font-mono">
            Trade #{alert.trade_id}
          </span>
        )}
      </div>

      {/* Price + Target Metrics */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs mb-3">
        {alert.current_price !== null && (
          <div>
            <span className="text-slate-400">Current Price</span>
            <span className="ml-1.5 font-mono font-semibold text-slate-700">
              {formatINR.format(alert.current_price)}
            </span>
          </div>
        )}
        {alert.target_level !== null && (
          <div>
            <span className="text-slate-400">Target</span>
            <span className="ml-1.5 font-mono font-semibold text-emerald-600">
              {formatINR.format(alert.target_level)}
            </span>
          </div>
        )}
        {alert.exit_qty !== null && (
          <div>
            <span className="text-slate-400">Exit Quantity</span>
            <span className="ml-1.5 font-mono font-semibold text-slate-700">
              {alert.exit_qty}
            </span>
          </div>
        )}
        {alert.exit_pct !== null && (
          <div>
            <span className="text-slate-400">Exit %</span>
            <span className="ml-1.5 font-mono font-semibold text-slate-700">
              {alert.exit_pct}%
            </span>
          </div>
        )}
        {alert.remaining_qty_after !== null && (
          <div>
            <span className="text-slate-400">Remaining</span>
            <span className="ml-1.5 font-mono font-semibold text-slate-700">
              {alert.remaining_qty_after}
            </span>
          </div>
        )}
      </div>

      {/* Action text */}
      {alert.action_text && (
        <div
          className={`rounded-lg px-3 py-2 mb-3 text-xs font-medium ${
            alert.alert_type === "SL_HIT"
              ? "bg-red-50 text-red-700"
              : "bg-amber-50 text-amber-700"
          }`}
        >
          {alert.action_text}
        </div>
      )}

      {/* Exit type explanation tooltip for context */}
      <div className="flex items-center gap-1 mb-3">
        {alert.alert_type === "SL_HIT" && (
          <span className="text-[10px] text-red-500">
            Mandatory full exit — Stop Loss <InfoTooltip termKey="SL" /> breached
          </span>
        )}
        {alert.alert_type === "2R_HIT" && (
          <span className="text-[10px] text-amber-600">
            2R Target <InfoTooltip termKey="2R" /> reached — exit 20% of position
          </span>
        )}
        {alert.alert_type === "NE_HIT" && (
          <span className="text-[10px] text-amber-600">
            Normal Exit <InfoTooltip termKey="NE" /> reached — exit 20% of position
          </span>
        )}
        {alert.alert_type === "GE_HIT" && (
          <span className="text-[10px] text-teal-600">
            Great Exit <InfoTooltip termKey="GE" /> reached — exit 40% of position
          </span>
        )}
        {alert.alert_type === "EE_HIT" && (
          <span className="text-[10px] text-emerald-600">
            Excellent Exit <InfoTooltip termKey="EE" /> reached — exit 80% of remaining
          </span>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-2 pt-3 border-t border-slate-100">
        <button
          disabled={isActing}
          onClick={() => onAct(alert.id)}
          className={`text-white text-xs font-medium px-4 py-2 rounded-lg transition-colors disabled:opacity-50 ${
            alert.alert_type === "SL_HIT"
              ? "bg-red-600 hover:bg-red-700"
              : "bg-teal-600 hover:bg-teal-700"
          }`}
        >
          Execute Exit
        </button>
        <button
          disabled={isActing}
          onClick={() => onDismiss(alert.id)}
          className="bg-white text-slate-500 text-xs font-medium px-4 py-2 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors disabled:opacity-50"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}
