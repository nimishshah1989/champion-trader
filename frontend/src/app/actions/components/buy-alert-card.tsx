"use client";

import { useState } from "react";
import { type ActionAlert } from "@/lib/api";
import { InfoTooltip } from "@/components/info-tooltip";

// ---------------------------------------------------------------------------
// Types & Helpers
// ---------------------------------------------------------------------------

interface ParsedTargets {
  target_2r?: number;
  target_ne?: number;
  target_ge?: number;
  target_ee?: number;
  [key: string]: unknown;
}

import { formatINR, formatINRCompact } from "@/lib/format";

function parseTargets(dataStr: string | null): ParsedTargets | null {
  if (!dataStr) return null;
  try {
    return JSON.parse(dataStr) as ParsedTargets;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// BuyAlertCard
// ---------------------------------------------------------------------------

interface BuyAlertCardProps {
  alert: ActionAlert;
  onAct: (id: number) => void;
  onDismiss: (id: number) => void;
  isActing: boolean;
}

const ALERT_TYPE_LABELS: Record<string, string> = {
  TRIGGER_BREAK: "Trigger Break",
  SL_HIT: "Stop Loss Hit",
  "2R_HIT": "2R Target Hit",
  NE_HIT: "Normal Exit Hit",
  GE_HIT: "Great Exit Hit",
  EE_HIT: "Excellent Exit Hit",
  FINAL_EXIT: "Final Exit",
};

export function BuyAlertCard({ alert, onAct, onDismiss, isActing }: BuyAlertCardProps) {
  const targets = parseTargets(alert.data);
  const [showBreakdown, setShowBreakdown] = useState(false);

  // Derived values for position breakdown
  const rptAmount =
    alert.account_value_used !== null && alert.rpt_pct_used !== null
      ? (alert.account_value_used * alert.rpt_pct_used) / 100
      : null;

  return (
    <div className="bg-white rounded-xl border border-slate-200 border-l-4 border-l-emerald-500 p-5 hover:border-slate-300 transition-colors">
      {/* Header: Symbol + Badge */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-base font-bold text-slate-800 tracking-wide">
            {alert.symbol}
          </span>
          <span className="bg-emerald-600 text-white rounded px-2 py-0.5 text-xs font-bold uppercase">
            BUY
          </span>
        </div>
        <span className="text-[10px] text-slate-400 uppercase tracking-wider font-medium">
          {ALERT_TYPE_LABELS[alert.alert_type] || alert.alert_type}
        </span>
      </div>

      {/* Price Metrics */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs mb-3">
        {alert.trigger_price !== null && (
          <div>
            <span className="text-slate-400">
              Trigger <InfoTooltip termKey="TRIGGER" />
            </span>
            <span className="ml-1.5 font-mono font-semibold text-slate-700">
              {formatINR.format(alert.trigger_price)}
            </span>
          </div>
        )}
        {alert.current_price !== null && (
          <div>
            <span className="text-slate-400">Current Price</span>
            <span className="ml-1.5 font-mono font-semibold text-emerald-600">
              {formatINR.format(alert.current_price)}
            </span>
          </div>
        )}
        {alert.suggested_entry_price !== null && (
          <div>
            <span className="text-slate-400">Entry</span>
            <span className="ml-1.5 font-mono font-semibold text-slate-700">
              {formatINR.format(alert.suggested_entry_price)}
            </span>
          </div>
        )}
        {alert.suggested_sl_price !== null && (
          <div>
            <span className="text-slate-400">
              Stop Loss <InfoTooltip termKey="SL" />
            </span>
            <span className="ml-1.5 font-mono font-semibold text-red-600">
              {formatINR.format(alert.suggested_sl_price)}
            </span>
          </div>
        )}
      </div>

      {/* Quantity row */}
      <div className="grid grid-cols-3 gap-x-4 text-xs mb-3">
        {alert.suggested_qty !== null && (
          <div>
            <span className="text-slate-400">
              Qty <InfoTooltip termKey="POSITION_SIZE" />
            </span>
            <span className="ml-1.5 font-mono font-semibold text-slate-700">
              {alert.suggested_qty}
            </span>
          </div>
        )}
        {alert.suggested_half_qty !== null && (
          <div>
            <span className="text-slate-400">
              Half Qty <InfoTooltip termKey="HALF_QTY" />
            </span>
            <span className="ml-1.5 font-mono font-semibold text-slate-700">
              {alert.suggested_half_qty}
            </span>
          </div>
        )}
        {alert.trp_pct !== null && (
          <div>
            <span className="text-slate-400">
              True Range % <InfoTooltip termKey="TRP" />
            </span>
            <span className="ml-1.5 font-mono font-semibold text-slate-700">
              {alert.trp_pct.toFixed(2)}%
            </span>
          </div>
        )}
      </div>

      {/* Targets row from parsed data */}
      {targets && (targets.target_2r || targets.target_ne || targets.target_ge || targets.target_ee) && (
        <div className="bg-slate-50 rounded-lg px-3 py-2 mb-3">
          <p className="text-[10px] text-slate-400 uppercase tracking-wider font-medium mb-1.5">
            Exit Targets
          </p>
          <div className="grid grid-cols-4 gap-2 text-xs">
            {targets.target_2r != null && (
              <div className="text-center">
                <span className="block text-[10px] text-slate-400">
                  2R <InfoTooltip termKey="2R" />
                </span>
                <span className="font-mono font-semibold text-slate-700">
                  {formatINRCompact.format(targets.target_2r as number)}
                </span>
              </div>
            )}
            {targets.target_ne != null && (
              <div className="text-center">
                <span className="block text-[10px] text-slate-400">
                  Normal <InfoTooltip termKey="NE" />
                </span>
                <span className="font-mono font-semibold text-slate-700">
                  {formatINRCompact.format(targets.target_ne as number)}
                </span>
              </div>
            )}
            {targets.target_ge != null && (
              <div className="text-center">
                <span className="block text-[10px] text-slate-400">
                  Great <InfoTooltip termKey="GE" />
                </span>
                <span className="font-mono font-semibold text-teal-600">
                  {formatINRCompact.format(targets.target_ge as number)}
                </span>
              </div>
            )}
            {targets.target_ee != null && (
              <div className="text-center">
                <span className="block text-[10px] text-slate-400">
                  Excellent <InfoTooltip termKey="EE" />
                </span>
                <span className="font-mono font-semibold text-emerald-600">
                  {formatINRCompact.format(targets.target_ee as number)}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Expandable Position Calculation Breakdown */}
      {alert.account_value_used !== null && alert.rpt_pct_used !== null && (
        <div className="mb-3">
          <button
            type="button"
            onClick={() => setShowBreakdown((prev) => !prev)}
            className="text-[11px] text-teal-600 hover:text-teal-700 font-medium flex items-center gap-1 transition-colors"
          >
            <svg
              className={`w-3 h-3 transition-transform duration-200 ${showBreakdown ? "rotate-90" : ""}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5l7 7-7 7"
              />
            </svg>
            {showBreakdown ? "Hide" : "Show"} position breakdown
          </button>

          {showBreakdown && (
            <div className="bg-slate-50 rounded-lg px-3 py-2.5 mt-1.5 text-xs text-slate-600 space-y-1.5">
              <div className="flex justify-between">
                <span>
                  Account Value <InfoTooltip termKey="AV" />
                </span>
                <span className="font-mono font-semibold text-slate-700">
                  {formatINR.format(alert.account_value_used)}
                </span>
              </div>
              <div className="flex justify-between">
                <span>
                  Risk Per Trade <InfoTooltip termKey="RPT" />
                </span>
                <span className="font-mono font-semibold text-slate-700">
                  {alert.rpt_pct_used}%
                  {rptAmount !== null && (
                    <span className="text-slate-400 ml-1">
                      ({formatINR.format(rptAmount)})
                    </span>
                  )}
                </span>
              </div>
              {alert.suggested_entry_price !== null && (
                <div className="flex justify-between">
                  <span>Entry Price</span>
                  <span className="font-mono font-semibold text-slate-700">
                    {formatINR.format(alert.suggested_entry_price)}
                  </span>
                </div>
              )}
              {alert.suggested_sl_price !== null && (
                <div className="flex justify-between">
                  <span>
                    Stop Loss <InfoTooltip termKey="SL" />
                  </span>
                  <span className="font-mono font-semibold text-red-600">
                    {formatINR.format(alert.suggested_sl_price)}
                    {alert.trp_pct !== null && (
                      <span className="text-slate-400 ml-1">
                        (TRP: {alert.trp_pct.toFixed(2)}%)
                      </span>
                    )}
                  </span>
                </div>
              )}
              {alert.suggested_qty !== null && (
                <div className="flex justify-between">
                  <span>Position Size</span>
                  <span className="font-mono font-semibold text-slate-700">
                    {alert.suggested_qty} shares
                  </span>
                </div>
              )}
              {alert.suggested_half_qty !== null && (
                <div className="flex justify-between">
                  <span>Half Quantity (entry split 50/50)</span>
                  <span className="font-mono font-semibold text-slate-700">
                    {alert.suggested_half_qty} shares
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Fallback: show AV/RPT context without breakdown if no full data */}
      {alert.account_value_used !== null &&
        alert.rpt_pct_used !== null &&
        !showBreakdown && (
          <p className="text-[10px] text-slate-400 mb-3">
            Account: {formatINRCompact.format(alert.account_value_used)}
            <span className="mx-1.5">|</span>
            Risk Per Trade: {alert.rpt_pct_used}%
          </p>
        )}

      {/* Action text */}
      {alert.action_text && (
        <p className="text-xs text-slate-600 italic mb-3 line-clamp-2">
          {alert.action_text}
        </p>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-2 pt-3 border-t border-slate-100">
        <button
          disabled={isActing}
          onClick={() => onAct(alert.id)}
          className="bg-emerald-600 text-white text-xs font-medium px-4 py-2 rounded-lg hover:bg-emerald-700 transition-colors disabled:opacity-50"
        >
          Take Trade
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
