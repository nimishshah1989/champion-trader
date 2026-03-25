"use client";

import { useCallback, useEffect, useState } from "react";
import {
  startPaperTrading,
  processPaperDay,
  getPaperStatus,
  stopPaperTrading,
  getSimulationRuns,
  type SimulationRun,
  type SimulationRunWithTrades,
} from "@/lib/api";
import { toast } from "sonner";
import { EquityChart } from "@/components/equity-chart";
import {
  formatINR,
  formatINRCompact,
  formatDate,
  formatPct,
  formatR,
  parseEquityCurve,
} from "./simulation-helpers";
import {
  StatsSkeletons,
  TableSkeletons,
  StatCard,
  SimStatusBadge,
  TradeStatusBadge,
  PreviousRunsList,
} from "./simulation-ui";

export function PaperTradingTab({
  allRuns,
  onRunsUpdated,
}: {
  allRuns: SimulationRun[];
  onRunsUpdated: () => void;
}) {
  const [activeSession, setActiveSession] =
    useState<SimulationRunWithTrades | null>(null);
  const [sessionLoading, setSessionLoading] = useState(true);
  const [processingDay, setProcessingDay] = useState(false);
  const [stoppingSession, setStoppingSession] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [capital, setCapital] = useState("100000");
  const [rptPct, setRptPct] = useState("0.5");
  const [name, setName] = useState("");
  const [starting, setStarting] = useState(false);

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
      if (result.entries.length > 0) parts.push(`Entries: ${result.entries.join(", ")}`);
      if (result.exits.length > 0) parts.push(`Exits: ${result.exits.join(", ")}`);
      parts.push(`Open: ${result.open_positions}`);

      toast.success(`Day processed (${result.date}): ${parts.join(" | ")}`);

      const fullStatus = await getPaperStatus(activeSession.id);
      setActiveSession(fullStatus);
      onRunsUpdated();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to process day";
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
      const message = err instanceof Error ? err.message : "Failed to stop session";
      toast.error(message);
    } finally {
      setStoppingSession(false);
    }
  }

  if (sessionLoading) {
    return (
      <div className="space-y-6">
        <StatsSkeletons count={4} />
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <div className="h-4 w-40 bg-slate-100 mb-4 rounded" />
          <TableSkeletons />
        </div>
      </div>
    );
  }

  if (error && !activeSession) {
    return (
      <div className="space-y-6">
        <div className="bg-white rounded-xl border border-slate-200 border-l-4 border-l-red-500 p-5">
          <p className="text-sm font-medium text-red-700">Error</p>
          <p className="text-xs text-slate-500 mt-1">{error}</p>
          <button onClick={checkActiveSession}
            className="text-xs text-teal-600 hover:text-teal-700 font-medium mt-2">Retry</button>
        </div>
        <PreviousRunsList runs={allRuns} runType="paper" onSelect={() => {}} />
      </div>
    );
  }

  if (!activeSession) {
    return (
      <div className="space-y-6">
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-base font-semibold text-slate-800 mb-1">Start Paper Trading</h3>
          <p className="text-xs text-slate-400 mb-4">
            Paper trade the Champion Trader strategy using live market data.
            Process one trading day at a time to simulate real execution.
          </p>
          <form onSubmit={handleStartPaper}>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 items-end">
              <div>
                <label className="text-xs text-slate-500 mb-1 block">Starting Capital</label>
                <input type="number" value={capital} onChange={(e) => setCapital(e.target.value)}
                  placeholder="1,00,000" min="10000" step="10000"
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
                  disabled={starting} />
              </div>
              <div>
                <label className="text-xs text-slate-500 mb-1 block">RPT %</label>
                <input type="number" value={rptPct} onChange={(e) => setRptPct(e.target.value)}
                  placeholder="0.5" min="0.1" max="2.0" step="0.1"
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
                  disabled={starting} />
              </div>
              <div>
                <label className="text-xs text-slate-500 mb-1 block">Name (optional)</label>
                <input type="text" value={name} onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. March Paper Test"
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
                  disabled={starting} />
              </div>
              <div>
                <button type="submit" disabled={starting}
                  className={`w-full font-medium px-6 py-2 rounded-lg transition-colors text-sm flex items-center justify-center gap-2 ${
                    starting ? "bg-slate-300 text-slate-500 cursor-not-allowed" : "bg-teal-600 text-white hover:bg-teal-700"
                  }`}>
                  {starting && (
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  )}
                  {starting ? "Starting..." : "Start Paper Trading"}
                </button>
              </div>
            </div>
          </form>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
          <svg className="w-12 h-12 mx-auto text-slate-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <p className="text-sm text-slate-500 mb-1">No active paper trading session</p>
          <p className="text-xs text-slate-400">Start a session above to simulate the Champion Trader strategy with live data.</p>
        </div>

        <PreviousRunsList runs={allRuns} runType="paper" onSelect={() => {}} />
      </div>
    );
  }

  // Active session dashboard
  const openTrades = activeSession.trades.filter(
    (t) => t.status === "OPEN" || t.status === "open" || t.status === "PARTIAL" || t.status === "partial"
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
            {activeSession.last_processed_date && ` | Last processed: ${formatDate(activeSession.last_processed_date)}`}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={handleProcessDay} disabled={processingDay || stoppingSession}
            className={`font-medium px-4 py-2 rounded-lg transition-colors text-sm flex items-center gap-2 ${
              processingDay ? "bg-slate-300 text-slate-500 cursor-not-allowed" : "bg-teal-600 text-white hover:bg-teal-700"
            }`}>
            {processingDay && (
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            )}
            {processingDay ? "Processing..." : "Process Today"}
          </button>
          <button onClick={handleStopSession} disabled={processingDay || stoppingSession}
            className={`font-medium px-4 py-2 rounded-lg transition-colors text-sm border ${
              stoppingSession ? "bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed"
                : "bg-white text-red-600 border-red-200 hover:bg-red-50"
            }`}>
            {stoppingSession ? "Stopping..." : "Stop Session"}
          </button>
        </div>
      </div>

      {/* Top stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Current Equity" value={formatINRCompact.format(currentEquity)} valueColor="text-teal-600"
          subtext={`Started at ${formatINRCompact.format(activeSession.starting_capital)}`} />
        <StatCard label="Cash Available"
          value={activeSession.final_capital != null ? formatINRCompact.format(activeSession.final_capital) : formatINRCompact.format(activeSession.starting_capital)}
          subtext="Available for new entries" />
        <StatCard label="Return %" value={formatPct(returnPct)} valueColor={returnPct >= 0 ? "text-emerald-600" : "text-red-600"}
          subtext={activeSession.total_pnl != null ? `P&L: ${formatINRCompact.format(activeSession.total_pnl)}` : undefined} />
        <StatCard label="Open Positions" value={String(openTrades.length)}
          subtext={`${closedTrades.length} closed | ${activeSession.total_trades} total`} />
      </div>

      {/* Open Positions */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-100">
          <h3 className="text-sm font-semibold text-slate-700">Open Positions ({openTrades.length})</h3>
        </div>
        {openTrades.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-sm text-slate-400">No open positions. Process the next trading day to look for entries.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Symbol</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Entry Price</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Qty</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">SL</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Target 2R</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Remaining Qty</th>
                  <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody>
                {openTrades.map((trade) => (
                  <tr key={trade.id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-slate-800">{trade.symbol}</td>
                    <td className="px-4 py-3 text-right font-mono text-slate-700">
                      {trade.entry_price != null ? formatINR.format(trade.entry_price) : "--"}</td>
                    <td className="px-4 py-3 text-right font-mono text-slate-700">{trade.total_qty ?? "--"}</td>
                    <td className="px-4 py-3 text-right font-mono text-red-600">
                      {trade.sl_price != null ? formatINR.format(trade.sl_price) : "--"}</td>
                    <td className="px-4 py-3 text-right font-mono text-emerald-600">
                      {trade.target_2r != null ? formatINR.format(trade.target_2r) : "--"}</td>
                    <td className="px-4 py-3 text-right font-mono text-slate-700">{trade.remaining_qty ?? "--"}</td>
                    <td className="px-4 py-3 text-center"><TradeStatusBadge status={trade.status} pnl={trade.gross_pnl} /></td>
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
          <h3 className="text-sm font-semibold text-slate-700">Closed Trades ({closedTrades.length})</h3>
        </div>
        {closedTrades.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-sm text-slate-400">No closed trades yet in this session.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Symbol</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Entry</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Exit</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Entry Price</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">P&L</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">R-Multiple</th>
                </tr>
              </thead>
              <tbody>
                {closedTrades.map((trade) => {
                  const pnl = trade.gross_pnl ?? 0;
                  return (
                    <tr key={trade.id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                      <td className="px-4 py-3 font-medium text-slate-800">{trade.symbol}</td>
                      <td className="px-4 py-3 text-slate-600">{trade.entry_date ? formatDate(trade.entry_date) : "--"}</td>
                      <td className="px-4 py-3 text-slate-600">{trade.exit_date ? formatDate(trade.exit_date) : "--"}</td>
                      <td className="px-4 py-3 text-right font-mono text-slate-700">
                        {trade.entry_price != null ? formatINR.format(trade.entry_price) : "--"}</td>
                      <td className={`px-4 py-3 text-right font-mono ${pnl >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                        {trade.gross_pnl != null ? formatINR.format(trade.gross_pnl) : "--"}</td>
                      <td className={`px-4 py-3 text-right font-mono ${(trade.r_multiple ?? 0) >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                        {formatR(trade.r_multiple)}</td>
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
          <h3 className="text-base font-semibold text-slate-800 mb-4">Equity Curve</h3>
          <EquityChart data={equityCurveData} startingCapital={activeSession.starting_capital} />
        </div>
      )}

      <PreviousRunsList runs={allRuns} runType="paper" onSelect={() => {}} />
    </div>
  );
}
