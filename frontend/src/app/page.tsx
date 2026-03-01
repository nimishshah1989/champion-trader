"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  getTrades,
  getLatestStance,
  getWatchlist,
  getWatchlistAlerts,
  getTradeStats,
  type Trade,
  type MarketStance,
  type WatchlistItem,
  type TradeStats,
} from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const formatINR = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

const STANCE_COLORS: Record<string, { color: string; bg: string }> = {
  STRONG: { color: "text-emerald-700", bg: "bg-emerald-50" },
  MODERATE: { color: "text-amber-700", bg: "bg-amber-50" },
  WEAK: { color: "text-red-700", bg: "bg-red-50" },
};

// ---------------------------------------------------------------------------
// Main Dashboard
// ---------------------------------------------------------------------------

export default function DashboardPage() {
  const [openTrades, setOpenTrades] = useState<Trade[]>([]);
  const [stats, setStats] = useState<TradeStats | null>(null);
  const [stance, setStance] = useState<MarketStance | null>(null);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [alerts, setAlerts] = useState<{ symbol: string; trigger_level: number; planned_sl_pct: number | null }[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchAll = useCallback(async () => {
    try {
      const [tradesData, stanceData, watchlistData, alertsData, statsData] = await Promise.allSettled([
        getTrades("OPEN"),
        getLatestStance(),
        getWatchlist(),
        getWatchlistAlerts(),
        getTradeStats(),
      ]);

      if (tradesData.status === "fulfilled") setOpenTrades(tradesData.value);
      if (stanceData.status === "fulfilled") setStance(stanceData.value);
      if (watchlistData.status === "fulfilled") setWatchlist(watchlistData.value);
      if (alertsData.status === "fulfilled") setAlerts(alertsData.value);
      if (statsData.status === "fulfilled") setStats(statsData.value);
    } catch {
      // Individual failures handled by allSettled
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // Derived values
  const readyStocks = watchlist.filter((w) => w.bucket === "READY");
  const nearStocks = watchlist.filter((w) => w.bucket === "NEAR");
  const totalOpenRisk = openTrades.reduce((sum, t) => sum + (t.rpt_amount ?? 0), 0);
  const stanceConfig = stance?.stance ? STANCE_COLORS[stance.stance] : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-slate-800">Dashboard</h1>
        <p className="text-sm text-slate-500 mt-0.5">Daily command centre — Champion Trader routine</p>
      </div>

      {/* ================================================================ */}
      {/* MORNING CHECK — 15 min */}
      {/* ================================================================ */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-slate-800 uppercase tracking-wider">Morning Check</h2>
          <span className="text-[10px] text-slate-400 bg-slate-100 rounded-full px-2 py-0.5 font-medium">15 min</span>
        </div>

        <div className="grid gap-4 md:grid-cols-4">
          {/* Open positions */}
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">Open Positions</p>
            {loading ? (
              <Skeleton className="h-9 w-12 bg-slate-100" />
            ) : (
              <span className="text-3xl font-bold text-slate-800 font-mono">{openTrades.length}</span>
            )}
            {!loading && openTrades.length > 0 && (
              <p className="text-[10px] text-slate-400 mt-1">
                {openTrades.map((t) => t.symbol).join(", ")}
              </p>
            )}
          </div>

          {/* Total open risk */}
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">Open Risk</p>
            {loading ? (
              <Skeleton className="h-9 w-24 bg-slate-100" />
            ) : (
              <span className="text-3xl font-bold text-slate-800 font-mono">
                {totalOpenRisk > 0 ? formatINR.format(totalOpenRisk) : "0"}
              </span>
            )}
            <p className="text-[10px] text-slate-400 mt-1">Max allowed: 10% of AV</p>
          </div>

          {/* Market stance */}
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">Market Stance</p>
            {loading ? (
              <Skeleton className="h-9 w-24 bg-slate-100" />
            ) : stanceConfig && stance?.stance ? (
              <span className={`text-3xl font-bold ${stanceConfig.color}`}>{stance.stance}</span>
            ) : (
              <span className="text-3xl font-bold text-slate-300">—</span>
            )}
            {stance && (
              <p className="text-[10px] text-slate-400 mt-1">
                RPT: {stance.rpt_pct ?? 0.5}% | Max pos: {stance.max_positions ?? "—"}
              </p>
            )}
            {!stance && !loading && (
              <Link href="/market-stance" className="text-[10px] text-teal-600 hover:text-teal-700 mt-1 block">
                Log today&apos;s stance &rarr;
              </Link>
            )}
          </div>

          {/* Trade stats */}
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">Performance</p>
            {loading ? (
              <Skeleton className="h-9 w-20 bg-slate-100" />
            ) : stats && stats.closed_trades > 0 ? (
              <>
                <span className={`text-3xl font-bold font-mono ${(stats.total_pnl ?? 0) >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                  {stats.win_rate != null ? `${stats.win_rate}%` : "—"}
                </span>
                <p className="text-[10px] text-slate-400 mt-1">
                  Win rate | ARR: {stats.arr ?? "—"} | P&L: {formatINR.format(stats.total_pnl)}
                </p>
              </>
            ) : (
              <>
                <span className="text-3xl font-bold text-slate-300">—</span>
                <p className="text-[10px] text-slate-400 mt-1">No closed trades yet</p>
              </>
            )}
          </div>
        </div>

        {/* Open positions table */}
        {!loading && openTrades.length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-100">
              <h3 className="text-xs font-semibold text-slate-600 uppercase tracking-wider">Open Positions — Check SL Levels</h3>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] text-slate-400 uppercase tracking-wider border-b border-slate-100">
                  <th className="px-5 py-2 font-medium">Symbol</th>
                  <th className="px-5 py-2 font-medium">Entry</th>
                  <th className="px-5 py-2 font-medium">Qty</th>
                  <th className="px-5 py-2 font-medium">SL Price</th>
                  <th className="px-5 py-2 font-medium">RPT Amt</th>
                  <th className="px-5 py-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {openTrades.map((trade) => (
                  <tr key={trade.id} className="border-b border-slate-50 hover:bg-slate-50/50">
                    <td className="px-5 py-2.5 font-bold text-slate-800">{trade.symbol}</td>
                    <td className="px-5 py-2.5 font-mono text-xs">{trade.avg_entry_price?.toFixed(2) ?? "—"}</td>
                    <td className="px-5 py-2.5 font-mono text-xs">{trade.remaining_qty ?? trade.total_qty}</td>
                    <td className="px-5 py-2.5 font-mono text-xs text-red-600 font-semibold">{trade.sl_price?.toFixed(2) ?? "—"}</td>
                    <td className="px-5 py-2.5 font-mono text-xs">{trade.rpt_amount ? formatINR.format(trade.rpt_amount) : "—"}</td>
                    <td className="px-5 py-2.5">
                      <span className="bg-blue-50 text-blue-700 border border-blue-200 rounded-full px-2 py-0.5 text-[10px] font-medium">
                        {trade.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ================================================================ */}
      {/* MARKET CLOSE — 30 min */}
      {/* ================================================================ */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-slate-800 uppercase tracking-wider">Market Close</h2>
          <span className="text-[10px] text-slate-400 bg-slate-100 rounded-full px-2 py-0.5 font-medium">30 min</span>
        </div>

        <div className="bg-white rounded-xl border border-slate-200">
          <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
            <h3 className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
              READY Stocks — Enter in Last 30 Minutes
            </h3>
            <Link href="/watchlist" className="text-[11px] text-teal-600 hover:text-teal-700 font-medium">
              Open Watchlist &rarr;
            </Link>
          </div>
          {loading ? (
            <div className="p-5 space-y-2">
              <Skeleton className="h-8 w-full bg-slate-100" />
              <Skeleton className="h-8 w-full bg-slate-100" />
            </div>
          ) : readyStocks.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-sm text-slate-400">No READY stocks in watchlist.</p>
              <Link href="/watchlist" className="text-xs text-teal-600 hover:text-teal-700 mt-1 inline-block">
                Add stocks to watchlist &rarr;
              </Link>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] text-slate-400 uppercase tracking-wider border-b border-slate-100">
                  <th className="px-5 py-2 font-medium">Symbol</th>
                  <th className="px-5 py-2 font-medium">Stage</th>
                  <th className="px-5 py-2 font-medium">Trigger Level</th>
                  <th className="px-5 py-2 font-medium">TRP%</th>
                  <th className="px-5 py-2 font-medium">Action</th>
                </tr>
              </thead>
              <tbody>
                {readyStocks.map((stock) => (
                  <tr key={stock.id} className="border-b border-slate-50 hover:bg-slate-50/50">
                    <td className="px-5 py-2.5 font-bold text-slate-800">{stock.symbol}</td>
                    <td className="px-5 py-2.5">
                      {stock.stage && (
                        <span className="bg-blue-50 text-blue-700 rounded-full px-2 py-0.5 text-[10px] font-semibold">
                          {stock.stage}
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-2.5 font-mono text-xs text-emerald-600 font-semibold">
                      {stock.trigger_level != null ? formatINR.format(stock.trigger_level) : "—"}
                    </td>
                    <td className="px-5 py-2.5 font-mono text-xs text-red-600">
                      {stock.planned_sl_pct != null ? `${stock.planned_sl_pct}%` : "—"}
                    </td>
                    <td className="px-5 py-2.5">
                      <Link
                        href={`/calculator?symbol=${encodeURIComponent(stock.symbol)}`}
                        className="text-[11px] font-medium px-2.5 py-1 rounded border border-teal-200 bg-teal-50 text-teal-700 hover:bg-teal-100 transition-colors"
                      >
                        Calculate Position
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Alerts for TradingView — quick copy list */}
        {alerts.length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <h3 className="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-3">
              Set These Alerts on TradingView
            </h3>
            <div className="space-y-1.5">
              {alerts.map((a) => (
                <div key={a.symbol} className="flex items-center gap-3 text-sm">
                  <span className="font-bold text-slate-800 w-28">{a.symbol}</span>
                  <span className="text-slate-400">crosses above</span>
                  <span className="font-mono font-semibold text-emerald-600">
                    {formatINR.format(a.trigger_level)}
                  </span>
                  {a.planned_sl_pct != null && (
                    <span className="text-[10px] text-slate-400">(SL: {a.planned_sl_pct}%)</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ================================================================ */}
      {/* POST-MARKET — 1 hour */}
      {/* ================================================================ */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-slate-800 uppercase tracking-wider">Post-Market Analysis</h2>
          <span className="text-[10px] text-slate-400 bg-slate-100 rounded-full px-2 py-0.5 font-medium">1 hour</span>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <Link href="/scanner" className="block">
            <div className="bg-white rounded-xl border border-slate-200 p-5 hover:border-teal-300 transition-colors">
              <h3 className="text-sm font-semibold text-slate-800 mb-1">Run Scans</h3>
              <p className="text-xs text-slate-400">PPC, NPC, Contraction scans post-market</p>
            </div>
          </Link>
          <Link href="/watchlist" className="block">
            <div className="bg-white rounded-xl border border-slate-200 p-5 hover:border-teal-300 transition-colors">
              <h3 className="text-sm font-semibold text-slate-800 mb-1">Update Watchlist</h3>
              <p className="text-xs text-slate-400">
                Move stocks between buckets ({nearStocks.length} NEAR, {readyStocks.length} READY)
              </p>
            </div>
          </Link>
          <Link href="/market-stance" className="block">
            <div className="bg-white rounded-xl border border-slate-200 p-5 hover:border-teal-300 transition-colors">
              <h3 className="text-sm font-semibold text-slate-800 mb-1">Log Market Stance</h3>
              <p className="text-xs text-slate-400">
                {stance ? `Current: ${stance.stance}` : "Not logged today"}
              </p>
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
}
