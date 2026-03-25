"use client";

import { useCallback, useState } from "react";
import {
  runBacktest,
  getBacktestResult,
  getBacktestProgress,
  type SimulationRun,
  type SimulationRunWithTrades,
  type BacktestProgress,
} from "@/lib/api";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import { EquityChart } from "@/components/equity-chart";
import { todayISO, parseEquityCurve, formatPct, formatINRCompact, formatDate } from "./simulation-helpers";
import { StatsSkeletons, BacktestStats, TradeLogTable, PreviousRunsList } from "./simulation-ui";

// ---------------------------------------------------------------------------
// Progress Indicator
// ---------------------------------------------------------------------------

const PHASE_LABELS: Record<string, string> = {
  initializing: "Initializing backtest...",
  fetching: "Downloading market data (~464 stocks)...",
  computing: "Pre-computing technical indicators...",
  scanning: "Simulating trading days...",
  done: "Completed",
  failed: "Failed",
};

function BacktestProgressBar({ progress }: { progress: BacktestProgress }) {
  const phase = progress.phase ?? "initializing";
  const pct = progress.progress_pct ?? 0;
  const phaseLabel = PHASE_LABELS[phase] ?? `${phase}...`;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <svg className="animate-spin h-5 w-5 text-teal-600" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-sm font-semibold text-slate-700">{phaseLabel}</span>
        </div>
        <span className="text-xs font-mono text-slate-400">
          {phase === "scanning" && progress.days_done != null && progress.days_total
            ? `${progress.days_done}/${progress.days_total} days`
            : `${pct.toFixed(0)}%`}
        </span>
      </div>

      <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
        <div
          className="h-full bg-teal-500 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>

      <div className="flex items-center justify-between mt-2">
        <p className="text-[10px] text-slate-400">
          {phase === "scanning" && progress.current_date
            ? `Processing ${progress.current_date}`
            : phase === "computing" && progress.stocks
              ? `${progress.stocks} stocks loaded`
              : phase === "fetching"
                ? "This may take 2-5 minutes on first run"
                : "Please wait..."}
        </p>
        {phase === "scanning" && progress.open_positions != null && (
          <p className="text-[10px] text-slate-400">{progress.open_positions} open positions</p>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Backtest Tab
// ---------------------------------------------------------------------------

export function BacktestTab({
  allRuns,
  onRunsUpdated,
}: {
  allRuns: SimulationRun[];
  onRunsUpdated: () => void;
}) {
  const [startDate, setStartDate] = useState("2024-01-01");
  const [endDate, setEndDate] = useState(todayISO());
  const [capital, setCapital] = useState("100000");
  const [rptPct, setRptPct] = useState("0.5");
  const [name, setName] = useState("");

  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState<BacktestProgress | null>(null);
  const [backtestResult, setBacktestResult] =
    useState<SimulationRunWithTrades | null>(null);
  const [resultLoading, setResultLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pollForResult = useCallback(
    async (runId: number) => {
      setResultLoading(true);
      setError(null);

      const MAX_POLL_MS = 45 * 60 * 1000;
      const POLL_INTERVAL_MS = 3000;
      const startTime = Date.now();

      const poll = async () => {
        try {
          const prog = await getBacktestProgress(runId);
          setProgress(prog);

          const status = prog.status.toUpperCase();

          if (status === "COMPLETED") {
            const result = await getBacktestResult(runId);
            setBacktestResult(result);
            setResultLoading(false);
            setIsRunning(false);
            setProgress(null);
            onRunsUpdated();
            toast.success(
              `Backtest complete: ${result.total_trades} trades, ${formatPct(result.total_return_pct)} return`
            );
            return;
          }

          if (status === "FAILED" || status === "ERROR") {
            setResultLoading(false);
            setIsRunning(false);
            setProgress(null);
            onRunsUpdated();
            const errMsg = prog.error_message ?? "Backtest failed";
            setError(errMsg);
            toast.error(`Backtest failed: ${errMsg}`);
            return;
          }

          if (Date.now() - startTime < MAX_POLL_MS) {
            setTimeout(poll, POLL_INTERVAL_MS);
          } else {
            setResultLoading(false);
            setIsRunning(false);
            setProgress(null);
            setError("Backtest polling timed out after 45 minutes. It may still be running on the server.");
            toast.error("Backtest polling timed out.");
          }
        } catch (err) {
          console.error("Backtest poll error:", err);
          if (Date.now() - startTime < MAX_POLL_MS) {
            setTimeout(poll, POLL_INTERVAL_MS * 2);
          } else {
            setResultLoading(false);
            setIsRunning(false);
            setProgress(null);
            setError("Lost connection while waiting for backtest results.");
            toast.error("Lost connection to server.");
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
              <label className="text-xs text-slate-500 mb-1 block">Start Date</label>
              <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)}
                className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
                disabled={isRunning} />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">End Date</label>
              <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)}
                className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
                disabled={isRunning} />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Starting Capital</label>
              <input type="number" value={capital} onChange={(e) => setCapital(e.target.value)}
                placeholder="1,00,000" min="10000" step="10000"
                className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
                disabled={isRunning} />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">RPT %</label>
              <input type="number" value={rptPct} onChange={(e) => setRptPct(e.target.value)}
                placeholder="0.5" min="0.1" max="2.0" step="0.1"
                className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
                disabled={isRunning} />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Name (optional)</label>
              <input type="text" value={name} onChange={(e) => setName(e.target.value)}
                placeholder="e.g. 2024 Bull Run"
                className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
                disabled={isRunning} />
            </div>
            <div>
              <button type="submit" disabled={isRunning}
                className={`w-full font-medium px-6 py-2 rounded-lg transition-colors text-sm flex items-center justify-center gap-2 ${
                  isRunning ? "bg-slate-300 text-slate-500 cursor-not-allowed" : "bg-teal-600 text-white hover:bg-teal-700"
                }`}>
                {isRunning && (
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
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
          {progress ? (
            <BacktestProgressBar progress={progress} />
          ) : (
            <>
              <StatsSkeletons count={8} />
              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <Skeleton className="h-4 w-32 bg-slate-100 mb-4" />
                <Skeleton className="h-64 w-full bg-slate-100 rounded-lg" />
              </div>
            </>
          )}
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
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-semibold text-slate-800">
                {backtestResult.name || `Backtest #${backtestResult.id}`} Results
              </h3>
              <p className="text-xs text-slate-400">
                {backtestResult.start_date ? formatDate(backtestResult.start_date) : "--"}{" "}
                to {backtestResult.end_date ? formatDate(backtestResult.end_date) : "--"}{" "}
                | Capital: {formatINRCompact.format(backtestResult.starting_capital)} |
                RPT: {backtestResult.rpt_pct}%
              </p>
            </div>
            <button onClick={() => setBacktestResult(null)}
              className="text-xs text-slate-400 hover:text-slate-600 font-medium">
              Clear Results
            </button>
          </div>

          <BacktestStats run={backtestResult} />

          {equityCurveData.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <h3 className="text-base font-semibold text-slate-800 mb-4">Equity Curve</h3>
              <EquityChart data={equityCurveData} startingCapital={backtestResult.starting_capital} />
            </div>
          )}

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

      <PreviousRunsList runs={allRuns} runType="backtest" onSelect={handleViewPreviousRun} />
    </div>
  );
}
