"use client";

import { useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import type { SimulationRun, SimulationTrade } from "@/lib/api";
import {
  formatINR,
  formatINRCompact,
  formatDate,
  formatPct,
  formatR,
} from "./simulation-helpers";

// ---------------------------------------------------------------------------
// Skeleton Loaders
// ---------------------------------------------------------------------------

export function StatsSkeletons({ count = 8 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="bg-white rounded-xl border border-slate-200 p-5">
          <Skeleton className="h-4 w-20 bg-slate-100 mb-2" />
          <Skeleton className="h-8 w-24 bg-slate-100" />
          <Skeleton className="h-3 w-16 bg-slate-100 mt-2" />
        </div>
      ))}
    </div>
  );
}

export function TableSkeletons() {
  return (
    <div className="space-y-1">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="flex items-center gap-4 px-5 py-3">
          <Skeleton className="h-5 w-24 bg-slate-100" />
          <Skeleton className="h-5 w-20 bg-slate-100" />
          <Skeleton className="h-5 w-16 bg-slate-100" />
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
// Stat Card
// ---------------------------------------------------------------------------

export function StatCard({
  label,
  value,
  subtext,
  valueColor,
}: {
  label: string;
  value: string;
  subtext?: string;
  valueColor?: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">
        {label}
      </p>
      <span
        className={`text-2xl font-bold font-mono tabular-nums ${
          valueColor || "text-slate-800"
        }`}
      >
        {value}
      </span>
      {subtext && (
        <p className="text-[10px] text-slate-400 mt-1">{subtext}</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Status Badges
// ---------------------------------------------------------------------------

export function SimStatusBadge({ status }: { status: string }) {
  const s = status.toUpperCase();
  let colorClasses = "bg-blue-50 text-blue-700 border-blue-200";

  if (s === "COMPLETED") {
    colorClasses = "bg-emerald-50 text-emerald-700 border-emerald-200";
  } else if (s === "RUNNING" || s === "ACTIVE") {
    colorClasses = "bg-amber-50 text-amber-700 border-amber-200";
  } else if (s === "FAILED" || s === "ERROR") {
    colorClasses = "bg-red-50 text-red-700 border-red-200";
  } else if (s === "STOPPED") {
    colorClasses = "bg-slate-50 text-slate-600 border-slate-200";
  }

  return (
    <span
      className={`${colorClasses} border rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase`}
    >
      {status}
    </span>
  );
}

export function TradeStatusBadge({
  status,
  pnl,
}: {
  status: string;
  pnl: number | null;
}) {
  let colorClasses = "bg-blue-50 text-blue-700 border-blue-200";

  if (status === "OPEN" || status === "open") {
    colorClasses = "bg-blue-50 text-blue-700 border-blue-200";
  } else if (status === "CLOSED" || status === "closed") {
    colorClasses =
      pnl != null && pnl >= 0
        ? "bg-emerald-50 text-emerald-700 border-emerald-200"
        : "bg-red-50 text-red-700 border-red-200";
  } else if (status === "PARTIAL" || status === "partial") {
    colorClasses = "bg-amber-50 text-amber-700 border-amber-200";
  }

  return (
    <span
      className={`${colorClasses} border rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase`}
    >
      {status}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Backtest Stats Grid
// ---------------------------------------------------------------------------

export function BacktestStats({ run }: { run: SimulationRun }) {
  const totalPnl = run.total_pnl ?? 0;
  const returnPct = run.total_return_pct ?? 0;
  const winRate = run.win_rate;
  const arr = run.arr;
  const expectancy = run.expectancy;
  const maxDd = run.max_drawdown_pct;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <StatCard
        label="Final Capital"
        value={run.final_capital != null ? formatINRCompact.format(run.final_capital) : "--"}
        valueColor="text-teal-600"
        subtext={`Started at ${formatINRCompact.format(run.starting_capital)}`}
      />
      <StatCard
        label="Total P&L"
        value={totalPnl !== 0 ? formatINRCompact.format(totalPnl) : "--"}
        valueColor={totalPnl >= 0 ? "text-emerald-600" : "text-red-600"}
        subtext="Gross realized"
      />
      <StatCard
        label="Return %"
        value={formatPct(returnPct)}
        valueColor={returnPct >= 0 ? "text-emerald-600" : "text-red-600"}
        subtext={
          run.start_date && run.end_date
            ? `${formatDate(run.start_date)} - ${formatDate(run.end_date)}`
            : undefined
        }
      />
      <StatCard
        label="Win Rate"
        value={winRate != null ? `${winRate.toFixed(1)}%` : "--"}
        valueColor={
          winRate != null
            ? winRate >= 40
              ? "text-emerald-600"
              : "text-red-600"
            : "text-slate-300"
        }
        subtext={`${run.win_count}W / ${run.loss_count}L`}
      />
      <StatCard
        label="ARR"
        value={arr != null ? arr.toFixed(2) : "--"}
        valueColor={
          arr != null
            ? arr >= 2
              ? "text-emerald-600"
              : "text-red-600"
            : "text-slate-300"
        }
        subtext="Target: 2.0+"
      />
      <StatCard
        label="Expectancy"
        value={expectancy != null ? `${expectancy.toFixed(2)}R` : "--"}
        valueColor={
          expectancy != null
            ? expectancy > 0
              ? "text-emerald-600"
              : "text-red-600"
            : "text-slate-300"
        }
        subtext="Per trade"
      />
      <StatCard
        label="Max Drawdown"
        value={maxDd != null ? `${maxDd.toFixed(2)}%` : "--"}
        valueColor={maxDd != null ? "text-red-600" : "text-slate-300"}
        subtext={
          run.max_drawdown_amount != null
            ? formatINRCompact.format(run.max_drawdown_amount)
            : undefined
        }
      />
      <StatCard
        label="Total Trades"
        value={String(run.total_trades)}
        subtext={`${run.win_count} wins, ${run.loss_count} losses`}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Trade Log Table
// ---------------------------------------------------------------------------

export function TradeLogTable({ trades }: { trades: SimulationTrade[] }) {
  if (trades.length === 0) {
    return (
      <div className="p-12 text-center">
        <p className="text-sm text-slate-400">No trades in this simulation.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200">
            <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Symbol
            </th>
            <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Entry Date
            </th>
            <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Entry Price
            </th>
            <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Exit Date
            </th>
            <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Qty
            </th>
            <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              SL
            </th>
            <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              P&L
            </th>
            <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              R-Multiple
            </th>
            <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Status
            </th>
          </tr>
        </thead>
        <tbody>
          {trades.map((trade) => {
            const pnl = trade.gross_pnl ?? 0;
            const isPnlPositive = pnl >= 0;

            return (
              <tr
                key={trade.id}
                className="border-b border-slate-100 hover:bg-slate-50 transition-colors"
              >
                <td className="px-4 py-3 text-sm font-medium text-slate-800">
                  {trade.symbol}
                </td>
                <td className="px-4 py-3 text-sm text-slate-600">
                  {trade.entry_date ? formatDate(trade.entry_date) : "--"}
                </td>
                <td className="px-4 py-3 text-sm text-right font-mono text-slate-700">
                  {trade.entry_price != null
                    ? formatINR.format(trade.entry_price)
                    : "--"}
                </td>
                <td className="px-4 py-3 text-sm text-slate-600">
                  {trade.exit_date ? formatDate(trade.exit_date) : "--"}
                </td>
                <td className="px-4 py-3 text-sm text-right font-mono text-slate-700">
                  {trade.total_qty ?? "--"}
                </td>
                <td className="px-4 py-3 text-sm text-right font-mono text-slate-700">
                  {trade.sl_price != null
                    ? formatINR.format(trade.sl_price)
                    : "--"}
                </td>
                <td
                  className={`px-4 py-3 text-sm text-right font-mono ${
                    isPnlPositive ? "text-emerald-600" : "text-red-600"
                  }`}
                >
                  {trade.gross_pnl != null
                    ? formatINR.format(trade.gross_pnl)
                    : "--"}
                </td>
                <td
                  className={`px-4 py-3 text-sm text-right font-mono ${
                    (trade.r_multiple ?? 0) >= 0
                      ? "text-emerald-600"
                      : "text-red-600"
                  }`}
                >
                  {formatR(trade.r_multiple)}
                </td>
                <td className="px-4 py-3 text-center">
                  <TradeStatusBadge
                    status={trade.status}
                    pnl={trade.gross_pnl}
                  />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Previous Runs List
// ---------------------------------------------------------------------------

export function PreviousRunsList({
  runs,
  runType,
  onSelect,
}: {
  runs: SimulationRun[];
  runType: string;
  onSelect: (runId: number) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  const filteredRuns = runs.filter((r) => r.run_type === runType);

  if (filteredRuns.length === 0) {
    return null;
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-5 py-3 hover:bg-slate-50/50 transition-colors"
      >
        <span className="text-sm font-semibold text-slate-700">
          Previous Runs ({filteredRuns.length})
        </span>
        <svg
          className={`w-4 h-4 text-slate-400 transition-transform duration-200 ${
            expanded ? "rotate-180" : ""
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>
      {expanded && (
        <div className="border-t border-slate-100">
          {filteredRuns.map((run) => (
            <div
              key={run.id}
              className="flex items-center justify-between px-5 py-3 border-b border-slate-100 last:border-0 hover:bg-slate-50 transition-colors"
            >
              <div className="flex-1">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium text-slate-800">
                    {run.name || `Run #${run.id}`}
                  </span>
                  <SimStatusBadge status={run.status} />
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  {run.start_date ? formatDate(run.start_date) : "--"}
                  {run.end_date ? ` to ${formatDate(run.end_date)}` : ""}
                  {" | "}
                  Capital: {formatINRCompact.format(run.starting_capital)}
                  {" | "}
                  RPT: {run.rpt_pct}%
                </p>
              </div>
              <div className="flex items-center gap-4">
                {run.total_return_pct != null && (
                  <span
                    className={`text-sm font-mono font-semibold ${
                      run.total_return_pct >= 0
                        ? "text-emerald-600"
                        : "text-red-600"
                    }`}
                  >
                    {formatPct(run.total_return_pct)}
                  </span>
                )}
                <span className="text-xs text-slate-400 font-mono">
                  {run.total_trades} trades
                </span>
                {run.status.toUpperCase() === "COMPLETED" && (
                  <button
                    onClick={() => onSelect(run.id)}
                    className="text-xs text-teal-600 hover:text-teal-700 font-medium"
                  >
                    View Details
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
