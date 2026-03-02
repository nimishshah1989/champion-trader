"use client";

import { useEffect, useState, useCallback } from "react";
import {
  runBacktest,
  getBacktestResult,
  startPaperTrading,
  processPaperDay,
  getPaperStatus,
  stopPaperTrading,
  getSimulationRuns,
  type SimulationRun,
  type SimulationRunWithTrades,
  type SimulationTrade,
} from "@/lib/api";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import { InfoBanner, Term } from "@/components/info-banner";
import { EquityChart } from "@/components/equity-chart";

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

type TabType = "BACKTEST" | "PAPER";

const TABS: { key: TabType; label: string }[] = [
  { key: "BACKTEST", label: "Historical Backtest" },
  { key: "PAPER", label: "Paper Trading" },
];

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

function parseEquityCurve(
  jsonStr: string | null
): { date: string; equity: number }[] {
  if (!jsonStr) return [];
  try {
    const parsed = JSON.parse(jsonStr);
    if (Array.isArray(parsed)) {
      return parsed.map((p: { date: string; equity: number }) => ({
        date: p.date,
        equity: p.equity,
      }));
    }
    return [];
  } catch {
    return [];
  }
}

function formatPct(value: number | null): string {
  if (value == null) return "--";
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

function formatR(value: number | null): string {
  if (value == null) return "--";
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}R`;
}

// ---------------------------------------------------------------------------
// Skeleton Loaders
// ---------------------------------------------------------------------------

function StatsSkeletons({ count = 8 }: { count?: number }) {
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

function TableSkeletons() {
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
// Stat Card Component
// ---------------------------------------------------------------------------

function StatCard({
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
// Status Badge
// ---------------------------------------------------------------------------

function SimStatusBadge({ status }: { status: string }) {
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

// ---------------------------------------------------------------------------
// Trade Status Badge
// ---------------------------------------------------------------------------

function TradeStatusBadge({
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
// Backtest Result Stats
// ---------------------------------------------------------------------------

function BacktestStats({ run }: { run: SimulationRun }) {
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

function TradeLogTable({ trades }: { trades: SimulationTrade[] }) {
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
// Previous Runs List (Collapsible)
// ---------------------------------------------------------------------------

function PreviousRunsList({
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

// ---------------------------------------------------------------------------
// Backtest Tab
// ---------------------------------------------------------------------------

function BacktestTab({
  allRuns,
  onRunsUpdated,
}: {
  allRuns: SimulationRun[];
  onRunsUpdated: () => void;
}) {
  // Form state
  const [startDate, setStartDate] = useState("2024-01-01");
  const [endDate, setEndDate] = useState(todayISO());
  const [capital, setCapital] = useState("100000");
  const [rptPct, setRptPct] = useState("0.5");
  const [name, setName] = useState("");

  // Run state
  const [isRunning, setIsRunning] = useState(false);
  const [backtestResult, setBacktestResult] =
    useState<SimulationRunWithTrades | null>(null);
  const [resultLoading, setResultLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Poll for backtest completion
  const pollForResult = useCallback(
    async (runId: number) => {
      setResultLoading(true);
      setError(null);

      const maxAttempts = 360; // Poll for up to 30 minutes (360 * 5 seconds)
      let attempts = 0;

      const poll = async () => {
        try {
          const result = await getBacktestResult(runId);
          const status = result.status.toUpperCase();

          if (
            status === "COMPLETED" ||
            status === "FAILED" ||
            status === "ERROR"
          ) {
            setBacktestResult(result);
            setResultLoading(false);
            setIsRunning(false);
            onRunsUpdated();

            if (status === "COMPLETED") {
              toast.success(
                `Backtest complete: ${result.total_trades} trades, ${formatPct(result.total_return_pct)} return`
              );
            } else {
              toast.error(
                `Backtest failed: ${result.error_message || "Unknown error"}`
              );
              setError(result.error_message || "Backtest failed");
            }
            return;
          }

          // Still running, poll again
          attempts++;
          if (attempts < maxAttempts) {
            setTimeout(poll, 5000);
          } else {
            setResultLoading(false);
            setIsRunning(false);
            setError("Backtest timed out. Check back later — it may still be running on the server.");
            toast.error("Backtest polling timed out after 30 minutes.");
          }
        } catch (err) {
          // If result is not ready yet (404 or similar), keep polling
          attempts++;
          if (attempts < maxAttempts) {
            setTimeout(poll, 5000);
          } else {
            setResultLoading(false);
            setIsRunning(false);
            const message =
              err instanceof Error ? err.message : "Failed to fetch result";
            setError(message);
            toast.error(message);
          }
        }
      };

      poll();
    },
    [onRunsUpdated]
  );

  async function handleRunBacktest(e: React.FormEvent) {
    e.preventDefault();

    const capitalNum = parseFloat(capital);
    const rptNum = parseFloat(rptPct);

    if (!startDate || !endDate) {
      toast.error("Start date and end date are required");
      return;
    }
    if (startDate >= endDate) {
      toast.error("Start date must be before end date");
      return;
    }
    if (isNaN(capitalNum) || capitalNum <= 0) {
      toast.error("Starting capital must be a positive number");
      return;
    }
    if (isNaN(rptNum) || rptNum <= 0 || rptNum > 2) {
      toast.error("RPT% must be between 0.1% and 2.0%");
      return;
    }

    setIsRunning(true);
    setBacktestResult(null);
    setError(null);

    try {
      const run = await runBacktest({
        start_date: startDate,
        end_date: endDate,
        starting_capital: capitalNum,
        rpt_pct: rptNum,
        name: name.trim() || undefined,
      });

      toast.info(
        `Backtest started (Run #${run.id}). This may take a few minutes...`
      );

      const runStatus = run.status.toUpperCase();
      // If the backtest returns immediately as completed
      if (runStatus === "COMPLETED") {
        const fullResult = await getBacktestResult(run.id);
        setBacktestResult(fullResult);
        setIsRunning(false);
        setResultLoading(false);
        onRunsUpdated();
        toast.success(
          `Backtest complete: ${fullResult.total_trades} trades, ${formatPct(fullResult.total_return_pct)} return`
        );
      } else if (runStatus === "FAILED" || runStatus === "ERROR") {
        setIsRunning(false);
        setError(run.error_message || "Backtest failed");
        toast.error(run.error_message || "Backtest failed");
        onRunsUpdated();
      } else {
        // Status is RUNNING — poll for completion
        pollForResult(run.id);
      }
    } catch (err) {
      setIsRunning(false);
      const message =
        err instanceof Error ? err.message : "Failed to start backtest";
      setError(message);
      toast.error(message);
    }
  }

  function handleViewPreviousRun(runId: number) {
    setResultLoading(true);
    setError(null);

    getBacktestResult(runId)
      .then((result) => {
        setBacktestResult(result);
        setResultLoading(false);
      })
      .catch((err) => {
        const message =
          err instanceof Error ? err.message : "Failed to load run";
        setError(message);
        setResultLoading(false);
        toast.error(message);
      });
  }

  const equityCurveData = backtestResult
    ? parseEquityCurve(backtestResult.equity_curve)
    : [];

  return (
    <div className="space-y-6">
      {/* Config Form */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h3 className="text-base font-semibold text-slate-800 mb-1">
          Backtest Configuration
        </h3>
        <p className="text-xs text-slate-400 mb-4">
          Run the Champion Trader strategy against historical data to evaluate
          performance.
        </p>

        <form onSubmit={handleRunBacktest}>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 items-end">
            <div>
              <label className="text-xs text-slate-500 mb-1 block">
                Start Date
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
                disabled={isRunning}
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">
                End Date
              </label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
                disabled={isRunning}
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">
                Starting Capital
              </label>
              <input
                type="number"
                value={capital}
                onChange={(e) => setCapital(e.target.value)}
                placeholder="1,00,000"
                min="10000"
                step="10000"
                className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
                disabled={isRunning}
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">
                RPT %
              </label>
              <input
                type="number"
                value={rptPct}
                onChange={(e) => setRptPct(e.target.value)}
                placeholder="0.5"
                min="0.1"
                max="2.0"
                step="0.1"
                className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
                disabled={isRunning}
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">
                Name (optional)
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. 2024 Bull Run"
                className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
                disabled={isRunning}
              />
            </div>
            <div>
              <button
                type="submit"
                disabled={isRunning}
                className={`w-full font-medium px-6 py-2 rounded-lg transition-colors text-sm flex items-center justify-center gap-2 ${
                  isRunning
                    ? "bg-slate-300 text-slate-500 cursor-not-allowed"
                    : "bg-teal-600 text-white hover:bg-teal-700"
                }`}
              >
                {isRunning && (
                  <svg
                    className="animate-spin h-4 w-4"
                    viewBox="0 0 24 24"
                    fill="none"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    />
                  </svg>
                )}
                {isRunning ? "Running..." : "Run Backtest"}
              </button>
            </div>
          </div>
        </form>
      </div>

      {/* Running / Loading State */}
      {(isRunning || resultLoading) && !backtestResult && (
        <div className="space-y-6">
          <StatsSkeletons count={8} />
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <Skeleton className="h-4 w-32 bg-slate-100 mb-4" />
            <Skeleton className="h-64 w-full bg-slate-100 rounded-lg" />
          </div>
        </div>
      )}

      {/* Error State */}
      {error && !isRunning && !resultLoading && (
        <div className="bg-white rounded-xl border border-slate-200 border-l-4 border-l-red-500 p-5">
          <p className="text-sm font-medium text-red-700">Backtest Error</p>
          <p className="text-xs text-slate-500 mt-1">{error}</p>
        </div>
      )}

      {/* Results */}
      {backtestResult && !isRunning && !resultLoading && (
        <div className="space-y-6">
          {/* Title */}
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-semibold text-slate-800">
                {backtestResult.name || `Backtest #${backtestResult.id}`} Results
              </h3>
              <p className="text-xs text-slate-400">
                {backtestResult.start_date
                  ? formatDate(backtestResult.start_date)
                  : "--"}{" "}
                to{" "}
                {backtestResult.end_date
                  ? formatDate(backtestResult.end_date)
                  : "--"}{" "}
                | Capital: {formatINRCompact.format(backtestResult.starting_capital)} |
                RPT: {backtestResult.rpt_pct}%
              </p>
            </div>
            <button
              onClick={() => setBacktestResult(null)}
              className="text-xs text-slate-400 hover:text-slate-600 font-medium"
            >
              Clear Results
            </button>
          </div>

          {/* Stats Grid */}
          <BacktestStats run={backtestResult} />

          {/* Equity Curve */}
          {equityCurveData.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <h3 className="text-base font-semibold text-slate-800 mb-4">
                Equity Curve
              </h3>
              <EquityChart
                data={equityCurveData}
                startingCapital={backtestResult.starting_capital}
              />
            </div>
          )}

          {/* Trade Log */}
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-700">
                Trade Log ({backtestResult.trades.length} trades)
              </h3>
            </div>
            <TradeLogTable trades={backtestResult.trades} />
          </div>
        </div>
      )}

      {/* Previous Runs */}
      <PreviousRunsList
        runs={allRuns}
        runType="backtest"
        onSelect={handleViewPreviousRun}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Paper Trading Tab
// ---------------------------------------------------------------------------

function PaperTradingTab({
  allRuns,
  onRunsUpdated,
}: {
  allRuns: SimulationRun[];
  onRunsUpdated: () => void;
}) {
  // Active session state
  const [activeSession, setActiveSession] =
    useState<SimulationRunWithTrades | null>(null);
  const [sessionLoading, setSessionLoading] = useState(true);
  const [processingDay, setProcessingDay] = useState(false);
  const [stoppingSession, setStoppingSession] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state (for starting new session)
  const [capital, setCapital] = useState("100000");
  const [rptPct, setRptPct] = useState("0.5");
  const [name, setName] = useState("");
  const [starting, setStarting] = useState(false);

  // Check for active paper session on load
  const checkActiveSession = useCallback(async () => {
    setSessionLoading(true);
    setError(null);

    try {
      const runs = await getSimulationRuns("paper");
      const activeRun = runs.find(
        (r) => r.status.toUpperCase() === "ACTIVE" || r.status.toUpperCase() === "RUNNING"
      );

      if (activeRun) {
        const fullStatus = await getPaperStatus(activeRun.id);
        setActiveSession(fullStatus);
      } else {
        setActiveSession(null);
      }
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to check session";
      setError(message);
    } finally {
      setSessionLoading(false);
    }
  }, []);

  useEffect(() => {
    checkActiveSession();
  }, [checkActiveSession]);

  async function handleStartPaper(e: React.FormEvent) {
    e.preventDefault();

    const capitalNum = parseFloat(capital);
    const rptNum = parseFloat(rptPct);

    if (isNaN(capitalNum) || capitalNum <= 0) {
      toast.error("Starting capital must be a positive number");
      return;
    }
    if (isNaN(rptNum) || rptNum <= 0 || rptNum > 2) {
      toast.error("RPT% must be between 0.1% and 2.0%");
      return;
    }

    setStarting(true);
    try {
      const run = await startPaperTrading({
        starting_capital: capitalNum,
        rpt_pct: rptNum,
        name: name.trim() || undefined,
      });

      toast.success(`Paper trading session started (Run #${run.id})`);

      // Fetch full status with trades
      const fullStatus = await getPaperStatus(run.id);
      setActiveSession(fullStatus);
      onRunsUpdated();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to start paper trading";
      toast.error(message);
    } finally {
      setStarting(false);
    }
  }

  async function handleProcessDay() {
    if (!activeSession) return;

    setProcessingDay(true);
    try {
      const result = await processPaperDay(activeSession.id);

      const parts: string[] = [];
      if (result.entries.length > 0) {
        parts.push(`Entries: ${result.entries.join(", ")}`);
      }
      if (result.exits.length > 0) {
        parts.push(`Exits: ${result.exits.join(", ")}`);
      }
      parts.push(`Open: ${result.open_positions}`);

      toast.success(
        `Day processed (${result.date}): ${parts.join(" | ")}`
      );

      // Refresh status
      const fullStatus = await getPaperStatus(activeSession.id);
      setActiveSession(fullStatus);
      onRunsUpdated();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to process day";
      toast.error(message);
    } finally {
      setProcessingDay(false);
    }
  }

  async function handleStopSession() {
    if (!activeSession) return;

    const confirmed = window.confirm(
      "Are you sure you want to stop the paper trading session? This will finalize all stats."
    );
    if (!confirmed) return;

    setStoppingSession(true);
    try {
      const finalRun = await stopPaperTrading(activeSession.id);

      toast.success(
        `Paper trading stopped. Return: ${formatPct(finalRun.total_return_pct)}, Trades: ${finalRun.total_trades}`
      );

      setActiveSession(null);
      onRunsUpdated();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to stop session";
      toast.error(message);
    } finally {
      setStoppingSession(false);
    }
  }

  // Loading state
  if (sessionLoading) {
    return (
      <div className="space-y-6">
        <StatsSkeletons count={4} />
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <Skeleton className="h-4 w-40 bg-slate-100 mb-4" />
          <TableSkeletons />
        </div>
      </div>
    );
  }

  // Error state
  if (error && !activeSession) {
    return (
      <div className="space-y-6">
        <div className="bg-white rounded-xl border border-slate-200 border-l-4 border-l-red-500 p-5">
          <p className="text-sm font-medium text-red-700">Error</p>
          <p className="text-xs text-slate-500 mt-1">{error}</p>
          <button
            onClick={checkActiveSession}
            className="text-xs text-teal-600 hover:text-teal-700 font-medium mt-2"
          >
            Retry
          </button>
        </div>
        <PreviousRunsList
          runs={allRuns}
          runType="paper"
          onSelect={() => {}}
        />
      </div>
    );
  }

  // No active session — show start form
  if (!activeSession) {
    return (
      <div className="space-y-6">
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-base font-semibold text-slate-800 mb-1">
            Start Paper Trading
          </h3>
          <p className="text-xs text-slate-400 mb-4">
            Paper trade the Champion Trader strategy using live market data.
            Process one trading day at a time to simulate real execution.
          </p>

          <form onSubmit={handleStartPaper}>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 items-end">
              <div>
                <label className="text-xs text-slate-500 mb-1 block">
                  Starting Capital
                </label>
                <input
                  type="number"
                  value={capital}
                  onChange={(e) => setCapital(e.target.value)}
                  placeholder="1,00,000"
                  min="10000"
                  step="10000"
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
                  disabled={starting}
                />
              </div>
              <div>
                <label className="text-xs text-slate-500 mb-1 block">
                  RPT %
                </label>
                <input
                  type="number"
                  value={rptPct}
                  onChange={(e) => setRptPct(e.target.value)}
                  placeholder="0.5"
                  min="0.1"
                  max="2.0"
                  step="0.1"
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
                  disabled={starting}
                />
              </div>
              <div>
                <label className="text-xs text-slate-500 mb-1 block">
                  Name (optional)
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. March Paper Test"
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
                  disabled={starting}
                />
              </div>
              <div>
                <button
                  type="submit"
                  disabled={starting}
                  className={`w-full font-medium px-6 py-2 rounded-lg transition-colors text-sm flex items-center justify-center gap-2 ${
                    starting
                      ? "bg-slate-300 text-slate-500 cursor-not-allowed"
                      : "bg-teal-600 text-white hover:bg-teal-700"
                  }`}
                >
                  {starting && (
                    <svg
                      className="animate-spin h-4 w-4"
                      viewBox="0 0 24 24"
                      fill="none"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                      />
                    </svg>
                  )}
                  {starting ? "Starting..." : "Start Paper Trading"}
                </button>
              </div>
            </div>
          </form>
        </div>

        {/* Empty state */}
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
          <div className="text-4xl mb-3 text-slate-300">
            <svg
              className="w-12 h-12 mx-auto text-slate-300"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
          </div>
          <p className="text-sm text-slate-500 mb-1">
            No active paper trading session
          </p>
          <p className="text-xs text-slate-400">
            Start a session above to simulate the Champion Trader strategy with
            live data.
          </p>
        </div>

        {/* Previous Runs */}
        <PreviousRunsList
          runs={allRuns}
          runType="paper"
          onSelect={() => {}}
        />
      </div>
    );
  }

  // Active session — show dashboard
  const openTrades = activeSession.trades.filter(
    (t) =>
      t.status === "OPEN" ||
      t.status === "open" ||
      t.status === "PARTIAL" ||
      t.status === "partial"
  );
  const closedTrades = activeSession.trades.filter(
    (t) => t.status === "CLOSED" || t.status === "closed"
  );

  const currentEquity = activeSession.final_capital ?? activeSession.starting_capital;
  const returnPct = activeSession.total_return_pct ?? 0;
  const equityCurveData = parseEquityCurve(activeSession.equity_curve);

  return (
    <div className="space-y-6">
      {/* Session header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-slate-800 flex items-center gap-2">
            {activeSession.name || `Paper Session #${activeSession.id}`}
            <SimStatusBadge status={activeSession.status} />
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Started: {activeSession.start_date ? formatDate(activeSession.start_date) : "--"}
            {activeSession.last_processed_date &&
              ` | Last processed: ${formatDate(activeSession.last_processed_date)}`}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleProcessDay}
            disabled={processingDay || stoppingSession}
            className={`font-medium px-4 py-2 rounded-lg transition-colors text-sm flex items-center gap-2 ${
              processingDay
                ? "bg-slate-300 text-slate-500 cursor-not-allowed"
                : "bg-teal-600 text-white hover:bg-teal-700"
            }`}
          >
            {processingDay && (
              <svg
                className="animate-spin h-4 w-4"
                viewBox="0 0 24 24"
                fill="none"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
            )}
            {processingDay ? "Processing..." : "Process Today"}
          </button>
          <button
            onClick={handleStopSession}
            disabled={processingDay || stoppingSession}
            className={`font-medium px-4 py-2 rounded-lg transition-colors text-sm border ${
              stoppingSession
                ? "bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed"
                : "bg-white text-red-600 border-red-200 hover:bg-red-50"
            }`}
          >
            {stoppingSession ? "Stopping..." : "Stop Session"}
          </button>
        </div>
      </div>

      {/* Top stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Current Equity"
          value={formatINRCompact.format(currentEquity)}
          valueColor="text-teal-600"
          subtext={`Started at ${formatINRCompact.format(activeSession.starting_capital)}`}
        />
        <StatCard
          label="Cash Available"
          value={
            activeSession.final_capital != null
              ? formatINRCompact.format(activeSession.final_capital)
              : formatINRCompact.format(activeSession.starting_capital)
          }
          subtext="Available for new entries"
        />
        <StatCard
          label="Return %"
          value={formatPct(returnPct)}
          valueColor={returnPct >= 0 ? "text-emerald-600" : "text-red-600"}
          subtext={
            activeSession.total_pnl != null
              ? `P&L: ${formatINRCompact.format(activeSession.total_pnl)}`
              : undefined
          }
        />
        <StatCard
          label="Open Positions"
          value={String(openTrades.length)}
          subtext={`${closedTrades.length} closed | ${activeSession.total_trades} total`}
        />
      </div>

      {/* Open Positions */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-100">
          <h3 className="text-sm font-semibold text-slate-700">
            Open Positions ({openTrades.length})
          </h3>
        </div>
        {openTrades.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-sm text-slate-400">
              No open positions. Process the next trading day to look for
              entries.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Symbol
                  </th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Entry Price
                  </th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Qty
                  </th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    SL
                  </th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Target 2R
                  </th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Remaining Qty
                  </th>
                  <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody>
                {openTrades.map((trade) => (
                  <tr
                    key={trade.id}
                    className="border-b border-slate-100 hover:bg-slate-50 transition-colors"
                  >
                    <td className="px-4 py-3 font-medium text-slate-800">
                      {trade.symbol}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-slate-700">
                      {trade.entry_price != null
                        ? formatINR.format(trade.entry_price)
                        : "--"}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-slate-700">
                      {trade.total_qty ?? "--"}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-red-600">
                      {trade.sl_price != null
                        ? formatINR.format(trade.sl_price)
                        : "--"}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-emerald-600">
                      {trade.target_2r != null
                        ? formatINR.format(trade.target_2r)
                        : "--"}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-slate-700">
                      {trade.remaining_qty ?? "--"}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <TradeStatusBadge
                        status={trade.status}
                        pnl={trade.gross_pnl}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Closed Trades */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-100">
          <h3 className="text-sm font-semibold text-slate-700">
            Closed Trades ({closedTrades.length})
          </h3>
        </div>
        {closedTrades.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-sm text-slate-400">
              No closed trades yet in this session.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Symbol
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Entry
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Exit
                  </th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Entry Price
                  </th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    P&L
                  </th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    R-Multiple
                  </th>
                </tr>
              </thead>
              <tbody>
                {closedTrades.map((trade) => {
                  const pnl = trade.gross_pnl ?? 0;
                  return (
                    <tr
                      key={trade.id}
                      className="border-b border-slate-100 hover:bg-slate-50 transition-colors"
                    >
                      <td className="px-4 py-3 font-medium text-slate-800">
                        {trade.symbol}
                      </td>
                      <td className="px-4 py-3 text-slate-600">
                        {trade.entry_date
                          ? formatDate(trade.entry_date)
                          : "--"}
                      </td>
                      <td className="px-4 py-3 text-slate-600">
                        {trade.exit_date ? formatDate(trade.exit_date) : "--"}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-slate-700">
                        {trade.entry_price != null
                          ? formatINR.format(trade.entry_price)
                          : "--"}
                      </td>
                      <td
                        className={`px-4 py-3 text-right font-mono ${
                          pnl >= 0 ? "text-emerald-600" : "text-red-600"
                        }`}
                      >
                        {trade.gross_pnl != null
                          ? formatINR.format(trade.gross_pnl)
                          : "--"}
                      </td>
                      <td
                        className={`px-4 py-3 text-right font-mono ${
                          (trade.r_multiple ?? 0) >= 0
                            ? "text-emerald-600"
                            : "text-red-600"
                        }`}
                      >
                        {formatR(trade.r_multiple)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Equity Curve */}
      {equityCurveData.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-base font-semibold text-slate-800 mb-4">
            Equity Curve
          </h3>
          <EquityChart
            data={equityCurveData}
            startingCapital={activeSession.starting_capital}
          />
        </div>
      )}

      {/* Previous Runs */}
      <PreviousRunsList
        runs={allRuns}
        runType="paper"
        onSelect={() => {}}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function SimulationPage() {
  const [activeTab, setActiveTab] = useState<TabType>("BACKTEST");
  const [allRuns, setAllRuns] = useState<SimulationRun[]>([]);
  const [runsLoading, setRunsLoading] = useState(true);

  const fetchRuns = useCallback(async () => {
    try {
      const runs = await getSimulationRuns();
      setAllRuns(runs);
    } catch (err) {
      console.error("Failed to fetch simulation runs:", err);
    } finally {
      setRunsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-xl font-semibold text-slate-800">
          Simulation
        </h1>
        <p className="text-sm text-slate-500">
          Backtest and paper trade the Champion Trader methodology
        </p>
      </div>

      {/* Info Banner */}
      <InfoBanner
        title="Quick Reference -- Simulation Engine"
        storageKey="simulation"
      >
        <Term label="Historical Backtest">
          Run the Champion Trader strategy against historical price data. The
          engine scans for PPC/NPC/Contraction setups, sizes positions using
          your RPT%, and executes the full exit framework (2R, NE, GE, EE).
        </Term>
        <Term label="Paper Trading">
          Simulate the strategy day-by-day on live market data. Process one day
          at a time to see entries, exits, and equity progression in real time.
        </Term>
        <Term label="RPT (Risk Per Trade)">
          Percentage of account risked per trade. Default 0.5%. Range:
          0.2%-1.0%. Lower RPT = smaller positions, more conservative.
        </Term>
        <Term label="Equity Curve">
          Daily portfolio value plot. Upward slope = edge is working. Deep
          drawdowns indicate strategy struggles in certain market regimes.
        </Term>
        <Term label="Expectancy">
          Expected R per trade. Formula: (Win Rate x Avg Win R) - (Loss Rate x
          Avg Loss R). Positive = you have an edge.
        </Term>
      </InfoBanner>

      {/* Tab Buttons */}
      <div className="flex items-center gap-2">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? "bg-teal-600 text-white"
                : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {runsLoading ? (
        <StatsSkeletons count={4} />
      ) : activeTab === "BACKTEST" ? (
        <BacktestTab allRuns={allRuns} onRunsUpdated={fetchRuns} />
      ) : (
        <PaperTradingTab allRuns={allRuns} onRunsUpdated={fetchRuns} />
      )}
    </div>
  );
}
