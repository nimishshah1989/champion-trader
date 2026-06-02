"use client";

import type { Trade } from "@/lib/api";
import { formatINR, formatDate, effectiveStop, isTrailing, isV2Trade } from "./trade-helpers";

// ---------------------------------------------------------------------------
// Signal badge — v2 stage at entry (S1B / S2)
// ---------------------------------------------------------------------------

function SignalBadge({ trade }: { trade: Trade }) {
  if (!trade.signal_type) return null;
  return (
    <span className="bg-violet-50 text-violet-700 border border-violet-200 rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide">
      {trade.signal_type}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Status Badge
// ---------------------------------------------------------------------------

export function StatusBadge({
  status,
  pnl,
}: {
  status: string;
  pnl: number | null;
}) {
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
                  {trade.avg_entry_price != null
                    ? formatINR.format(trade.avg_entry_price)
                    : "--"}
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

          {/* Column 2: Stop & trail (v2 chandelier) */}
          <div className="space-y-2">
            <p className="text-[10px] text-slate-400 uppercase tracking-wider font-medium">
              Stop &amp; Trail
            </p>
            <div className="space-y-1">
              <div className="flex justify-between">
                <span className="text-slate-400">Initial SL (1R)</span>
                <span className="font-mono font-semibold text-slate-600">
                  {trade.sl_price != null ? formatINR.format(trade.sl_price) : "--"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">
                  Current Stop{isTrailing(trade) && <span className="text-emerald-500 ml-0.5">&uarr;</span>}
                </span>
                <span className="font-mono font-bold text-red-600">
                  {effectiveStop(trade) != null ? formatINR.format(effectiveStop(trade) as number) : "--"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Highest High</span>
                <span className="font-mono font-semibold text-slate-700">
                  {trade.highest_high != null ? formatINR.format(trade.highest_high) : "--"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">RPT Amount</span>
                <span className="font-mono font-semibold text-slate-700">
                  {trade.rpt_amount != null ? formatINR.format(trade.rpt_amount) : "--"}
                </span>
              </div>
            </div>
          </div>

          {/* Column 3: Attribution (v2) — or the legacy R-ladder targets */}
          {isV2Trade(trade) ? (
            <div className="space-y-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-wider font-medium">
                Attribution{trade.strategy_version ? ` · ${trade.strategy_version}` : ""}
              </p>
              <div className="space-y-1">
                <div className="flex justify-between">
                  <span className="text-slate-400">Signal</span>
                  <span className="font-medium text-violet-700">
                    {trade.signal_type ?? "--"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Regime @ entry</span>
                  <span className="font-medium text-slate-700">
                    {trade.regime_at_entry ?? "--"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Avg TRP @ entry</span>
                  <span className="font-mono font-semibold text-slate-700">
                    {trade.avg_trp_at_entry != null ? `${trade.avg_trp_at_entry.toFixed(2)}%` : "--"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Vol ratio @ entry</span>
                  <span
                    className={`font-mono font-semibold ${
                      trade.volume_ratio_at_entry != null && trade.volume_ratio_at_entry >= 2
                        ? "text-emerald-600"
                        : "text-slate-700"
                    }`}
                  >
                    {trade.volume_ratio_at_entry != null ? `${trade.volume_ratio_at_entry.toFixed(2)}x` : "--"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">ATR @ entry</span>
                  <span className="font-mono font-semibold text-slate-700">
                    {trade.atr_at_entry != null ? trade.atr_at_entry.toFixed(2) : "--"}
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-wider font-medium">
                Targets <span className="text-slate-300">(legacy)</span>
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
          )}

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
                  {trade.r_multiple != null
                    ? `${trade.r_multiple.toFixed(2)}R`
                    : "--"}
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
// Trade Table Row (expand/collapse logic)
// ---------------------------------------------------------------------------

export function TradeRow({
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
            <SignalBadge trade={trade} />
          </div>
        </td>

        {/* Entry Date */}
        <td className="px-5 py-2.5 text-slate-500 text-xs">
          {formatDate(trade.entry_date)}
        </td>

        {/* Entry Price */}
        <td className="px-5 py-2.5 text-right font-mono tabular-nums text-xs text-slate-700">
          {trade.avg_entry_price != null
            ? formatINR.format(trade.avg_entry_price)
            : "--"}
        </td>

        {/* Qty */}
        <td className="px-5 py-2.5 text-right font-mono tabular-nums text-xs text-slate-700">
          {trade.total_qty ?? "--"}
        </td>

        {/* Remaining */}
        <td className="px-5 py-2.5 text-right font-mono tabular-nums text-xs text-slate-700">
          {trade.remaining_qty ?? trade.total_qty ?? "--"}
        </td>

        {/* Current stop (v2 chandelier trail; falls back to the initial 1R) */}
        <td className="px-5 py-2.5 text-right font-mono tabular-nums text-xs text-red-600 font-semibold">
          {effectiveStop(trade) != null ? (
            <span className="inline-flex items-center justify-end gap-0.5">
              {isTrailing(trade) && <span className="text-emerald-500" title="trailing stop ratcheted up">&uarr;</span>}
              {formatINR.format(effectiveStop(trade) as number)}
            </span>
          ) : (
            "--"
          )}
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
