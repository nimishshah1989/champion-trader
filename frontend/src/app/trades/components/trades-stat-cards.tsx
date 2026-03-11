"use client";

import { type TradeStats } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { formatINRCompact } from "@/lib/format";

// ---------------------------------------------------------------------------
// Skeleton Loaders
// ---------------------------------------------------------------------------

export function StatsSkeletons() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="bg-white rounded-xl border border-slate-200 p-5">
          <Skeleton className="h-4 w-20 bg-slate-100 mb-2" />
          <Skeleton className="h-8 w-16 bg-slate-100" />
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
          <Skeleton className="h-5 w-12 bg-slate-100" />
          <Skeleton className="h-5 w-12 bg-slate-100" />
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
// Stat Cards
// ---------------------------------------------------------------------------

const WIN_RATE_THRESHOLD = 40;
const ARR_THRESHOLD = 2;

export function StatCards({
  stats,
  loading,
}: {
  stats: TradeStats | null;
  loading: boolean;
}) {
  if (loading) return <StatsSkeletons />;

  const totalTrades = stats?.total_trades ?? 0;
  const winRate = stats?.win_rate;
  const arr = stats?.arr;
  const totalPnl = stats?.total_pnl ?? 0;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {/* Total Trades */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">
          Total Trades
        </p>
        <span className="text-3xl font-bold text-slate-800 font-mono tabular-nums">
          {totalTrades}
        </span>
        <p className="text-[10px] text-slate-400 mt-1">
          {stats
            ? `${stats.open_trades} open, ${stats.closed_trades} closed`
            : "No data"}
        </p>
      </div>

      {/* Win Rate */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">
          Win Rate
        </p>
        {winRate != null ? (
          <span
            className={`text-3xl font-bold font-mono tabular-nums ${
              winRate >= WIN_RATE_THRESHOLD ? "text-emerald-600" : "text-red-600"
            }`}
          >
            {winRate.toFixed(1)}%
          </span>
        ) : (
          <span className="text-3xl font-bold text-slate-300">--</span>
        )}
        <p className="text-[10px] text-slate-400 mt-1">
          {stats
            ? `${stats.win_count}W / ${stats.loss_count}L`
            : "No closed trades"}
        </p>
      </div>

      {/* Average Risk-Reward */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">
          Avg Reward:Risk
        </p>
        {arr != null ? (
          <span
            className={`text-3xl font-bold font-mono tabular-nums ${
              arr >= ARR_THRESHOLD ? "text-emerald-600" : "text-red-600"
            }`}
          >
            {arr.toFixed(2)}
          </span>
        ) : (
          <span className="text-3xl font-bold text-slate-300">--</span>
        )}
        <p className="text-[10px] text-slate-400 mt-1">Target: 2.0+</p>
      </div>

      {/* Total P&L */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">
          Total P&L
        </p>
        <span
          className={`text-2xl font-bold font-mono tabular-nums ${
            totalPnl >= 0 ? "text-emerald-600" : "text-red-600"
          }`}
        >
          {totalPnl !== 0 ? formatINRCompact.format(totalPnl) : "--"}
        </span>
        <p className="text-[10px] text-slate-400 mt-1">Gross realized P&L</p>
      </div>
    </div>
  );
}
