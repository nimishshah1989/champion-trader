"use client";

import { useEffect, useState, useCallback } from "react";
import { getTradeStats, type TradeStats } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { InfoTooltip } from "@/components/info-tooltip";
import { formatINRCompact } from "./trade-helpers";

// ---------------------------------------------------------------------------
// Skeleton Loaders
// ---------------------------------------------------------------------------

function PerformanceSkeletons() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="bg-white rounded-xl border border-slate-200 p-5">
          <Skeleton className="h-4 w-24 bg-slate-100 mb-3" />
          <Skeleton className="h-8 w-20 bg-slate-100 mb-2" />
          <Skeleton className="h-3 w-28 bg-slate-100" />
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Expectancy Calculation
// ---------------------------------------------------------------------------

function computeExpectancy(stats: TradeStats): number | null {
  if (
    stats.closed_trades === 0 ||
    stats.win_rate == null ||
    stats.avg_r_multiple == null
  ) {
    return null;
  }

  const winRate = stats.win_rate / 100;
  const lossRate = 1 - winRate;

  // Average win R and average loss R are not directly available from the API.
  // We use avg_r_multiple (average across ALL closed trades) and win/loss counts
  // to derive a simplified expectancy:
  //   Expectancy = avg_r_multiple (which is already the weighted average)
  // This is equivalent to (WR * AvgWinR) - (LR * AvgLossR) when computed
  // across all trades. The avg_r_multiple from the API IS the expectancy.
  //
  // However, if ARR is available we can use the standard formula approximation:
  // Expectancy ~ (WR * ARR) - LR  (assuming avg loss = 1R)
  if (stats.arr != null) {
    return winRate * stats.arr - lossRate;
  }

  return stats.avg_r_multiple;
}

// ---------------------------------------------------------------------------
// Performance Tab
// ---------------------------------------------------------------------------

export function PerformanceTab() {
  const [stats, setStats] = useState<TradeStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    try {
      setError(null);
      const data = await getTradeStats();
      setStats(data);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to fetch trade stats";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  const expectancy = stats ? computeExpectancy(stats) : null;

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  return (
    <div className="space-y-6">
      {/* Loading */}
      {loading && <PerformanceSkeletons />}

      {/* Error */}
      {error && !loading && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <p className="text-sm text-red-600 font-medium mb-2">
            Failed to load performance metrics
          </p>
          <p className="text-xs text-red-400 mb-3">{error}</p>
          <button
            onClick={() => {
              setLoading(true);
              fetchStats();
            }}
            className="bg-red-600 text-white text-xs font-medium px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Stats Cards */}
      {!loading && !error && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Win Rate */}
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1 flex items-center gap-1">
              Win Rate
              <InfoTooltip termKey="WIN_RATE" />
            </p>
            {stats?.win_rate != null ? (
              <span
                className={`text-3xl font-bold font-mono tabular-nums ${
                  stats.win_rate >= 40 ? "text-emerald-600" : "text-red-600"
                }`}
              >
                {stats.win_rate.toFixed(1)}%
              </span>
            ) : (
              <span className="text-3xl font-bold text-slate-300">--</span>
            )}
            <p className="text-[10px] text-slate-400 mt-1">
              {stats
                ? `${stats.win_count}W / ${stats.loss_count}L of ${stats.closed_trades} closed`
                : "No closed trades"}
            </p>
            <p className="text-[10px] text-slate-400">Target: &gt;40%</p>
          </div>

          {/* Average Risk-Reward */}
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1 flex items-center gap-1">
              Average Risk-Reward
              <InfoTooltip termKey="ARR" />
            </p>
            {stats?.arr != null ? (
              <span
                className={`text-3xl font-bold font-mono tabular-nums ${
                  stats.arr >= 2 ? "text-emerald-600" : "text-red-600"
                }`}
              >
                {stats.arr.toFixed(2)}
              </span>
            ) : (
              <span className="text-3xl font-bold text-slate-300">--</span>
            )}
            <p className="text-[10px] text-slate-400 mt-1">Target: &gt;2.0</p>
          </div>

          {/* Expectancy per Trade */}
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1 flex items-center gap-1">
              Expectancy per Trade
              <InfoTooltip termKey="EXPECTANCY" />
            </p>
            {expectancy != null ? (
              <span
                className={`text-3xl font-bold font-mono tabular-nums ${
                  expectancy >= 0 ? "text-emerald-600" : "text-red-600"
                }`}
              >
                {expectancy >= 0 ? "+" : ""}
                {expectancy.toFixed(2)}R
              </span>
            ) : (
              <span className="text-3xl font-bold text-slate-300">--</span>
            )}
            <p className="text-[10px] text-slate-400 mt-1">
              (Win Rate x Avg Win R) - (Loss Rate x Avg Loss R)
            </p>
          </div>

          {/* Total P&L */}
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">
              Total P&L
            </p>
            {stats && stats.total_pnl !== 0 ? (
              <span
                className={`text-2xl font-bold font-mono tabular-nums ${
                  stats.total_pnl >= 0 ? "text-emerald-600" : "text-red-600"
                }`}
              >
                {formatINRCompact.format(stats.total_pnl)}
              </span>
            ) : (
              <span className="text-3xl font-bold text-slate-300">--</span>
            )}
            <p className="text-[10px] text-slate-400 mt-1">
              All-time gross realized P&L
            </p>
          </div>
        </div>
      )}

      {/* Empty state for zero closed trades */}
      {!loading && !error && stats && stats.closed_trades === 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
          <p className="text-sm text-slate-400 mb-1">
            No closed trades yet. Performance metrics will appear once you close
            your first trade.
          </p>
        </div>
      )}

      {/* Chart Placeholders */}
      {!loading && !error && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Monthly P&L Bar Chart */}
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <div className="mb-2">
              <h3 className="text-base font-semibold text-slate-800">
                Monthly P&L
              </h3>
              <p className="text-xs text-slate-400">
                Bar chart -- each bar is one calendar month
              </p>
            </div>
            <div className="h-48 flex items-center justify-center border border-dashed border-slate-200 rounded-lg bg-slate-50/50">
              <p className="text-sm text-slate-400">Charts -- Coming Soon</p>
            </div>
          </div>

          {/* R-Multiple Distribution Histogram */}
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <div className="mb-2 flex items-center gap-1.5">
              <h3 className="text-base font-semibold text-slate-800">
                R-Multiple Distribution
              </h3>
              <InfoTooltip termKey="R_MULTIPLE" />
            </div>
            <p className="text-xs text-slate-400 mb-2">
              Histogram of R-multiples across all closed trades
            </p>
            <div className="h-48 flex items-center justify-center border border-dashed border-slate-200 rounded-lg bg-slate-50/50">
              <p className="text-sm text-slate-400">Charts -- Coming Soon</p>
            </div>
          </div>
        </div>
      )}

      {/* Max Drawdown Placeholder */}
      {!loading && !error && (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center gap-1.5 mb-1">
            <p className="text-xs text-slate-400 font-medium uppercase tracking-wide">
              Maximum Drawdown
            </p>
            <InfoTooltip termKey="DRAWDOWN" />
          </div>
          <span className="text-2xl font-bold text-slate-300 font-mono tabular-nums">
            --
          </span>
          <p className="text-[10px] text-slate-400 mt-1">
            Peak-to-trough equity decline. Available after equity curve tracking
            is enabled.
          </p>
        </div>
      )}
    </div>
  );
}
