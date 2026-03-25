"use client";

import Link from "next/link";
import { Skeleton } from "@/components/ui/skeleton";
import type { Trade, WatchlistItem, TradeStats, MarketStance, HealthStatus } from "@/lib/api";

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
// JOB_META — human-readable names + schedule descriptions
// ---------------------------------------------------------------------------

const JOB_META: Record<string, { label: string; schedule: string }> = {
  daily_scanner:   { label: "Daily Scanner",    schedule: "4:00 PM" },
  exit_monitor:    { label: "Exit Monitor",      schedule: "Every 2 min" },
  entry_monitor:   { label: "Entry Monitor",     schedule: "3:00-3:30 PM" },
  risk_guardian:   { label: "Risk Guardian",     schedule: "Every 10 min" },
  regime_classifier: { label: "Regime Classifier", schedule: "4:45 PM" },
  cio_agent:       { label: "CIO Brief",         schedule: "5:00 PM" },
  corpus_updater:  { label: "Corpus Updater",    schedule: "5:30 PM" },
  learning_agent:  { label: "Learning Agent",    schedule: "Every 30 min" },
  shadow_portfolio:{ label: "Shadow Portfolio",  schedule: "Every 30 min" },
  autooptimize:    { label: "AutoOptimize",      schedule: "6:00 PM" },
};

function formatNextRun(nextRunStr: string): string {
  try {
    const d = new Date(nextRunStr);
    if (isNaN(d.getTime())) return nextRunStr;
    return d.toLocaleString("en-IN", {
      day: "numeric", month: "short",
      hour: "2-digit", minute: "2-digit", hour12: true,
    });
  } catch (err) {
    console.error("Failed to parse next run date:", err);
    return nextRunStr;
  }
}

// ---------------------------------------------------------------------------
// SystemStatusBanner
// ---------------------------------------------------------------------------

export function SystemStatusBanner({ health }: { health: HealthStatus | null }) {
  const schedulerRunning = health?.scheduler === "running";

  return (
    <div className={`rounded-xl border p-4 ${schedulerRunning ? "bg-emerald-50 border-emerald-200" : "bg-red-50 border-red-200"}`}>
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <span className={`relative flex h-2.5 w-2.5`}>
            {schedulerRunning && (
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            )}
            <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${schedulerRunning ? "bg-emerald-500" : "bg-red-400"}`} />
          </span>
          <span className={`text-sm font-semibold ${schedulerRunning ? "text-emerald-800" : "text-red-700"}`}>
            {schedulerRunning
              ? `System Running — ${health?.scheduled_jobs ?? 0} jobs scheduled`
              : "System Offline — start the backend to enable automation"}
          </span>
        </div>
        {!schedulerRunning && (
          <code className="text-[11px] bg-red-100 text-red-700 border border-red-200 rounded px-2 py-1 font-mono">
            bash scripts/setup_autostart.sh
          </code>
        )}
      </div>

      {/* Job grid — only show when running */}
      {schedulerRunning && health && health.jobs.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1">
          {health.jobs.map((job) => {
            const meta = JOB_META[job.id];
            return (
              <div key={job.id} className="flex items-center gap-1.5 text-[11px] text-emerald-700">
                <span className="font-medium">{meta?.label ?? job.id}</span>
                <span className="text-emerald-500">·</span>
                <span className="font-mono text-emerald-600">{meta?.schedule ?? "scheduled"}</span>
                <span className="text-emerald-400">→</span>
                <span className="text-emerald-500 tabular-nums">{formatNextRun(job.next_run)}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// MorningCheckCards
// ---------------------------------------------------------------------------

export function MorningCheckCards({
  openTrades,
  totalOpenRisk,
  stance,
  stats,
  loading,
}: {
  openTrades: Trade[];
  totalOpenRisk: number;
  stance: MarketStance | null;
  stats: TradeStats | null;
  loading: boolean;
}) {
  const stanceConfig = stance?.stance ? STANCE_COLORS[stance.stance] : null;

  return (
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
          <span className="text-3xl font-bold text-slate-300">&mdash;</span>
        )}
        {stance && (
          <p className="text-[10px] text-slate-400 mt-1">
            RPT: {stance.rpt_pct ?? 0.5}% | Max pos: {stance.max_positions ?? "&mdash;"}
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
              {stats.win_rate != null ? `${stats.win_rate}%` : "&mdash;"}
            </span>
            <p className="text-[10px] text-slate-400 mt-1">
              Win rate | ARR: {stats.arr ?? "&mdash;"} | P&L: {formatINR.format(stats.total_pnl)}
            </p>
          </>
        ) : (
          <>
            <span className="text-3xl font-bold text-slate-300">&mdash;</span>
            <p className="text-[10px] text-slate-400 mt-1">No closed trades yet</p>
          </>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// OpenPositionsTable
// ---------------------------------------------------------------------------

export function OpenPositionsTable({ trades }: { trades: Trade[] }) {
  if (trades.length === 0) return null;

  return (
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
          {trades.map((trade) => (
            <tr key={trade.id} className="border-b border-slate-50 hover:bg-slate-50/50">
              <td className="px-5 py-2.5 font-bold text-slate-800">{trade.symbol}</td>
              <td className="px-5 py-2.5 font-mono text-xs">{trade.avg_entry_price?.toFixed(2) ?? "&mdash;"}</td>
              <td className="px-5 py-2.5 font-mono text-xs">{trade.remaining_qty ?? trade.total_qty}</td>
              <td className="px-5 py-2.5 font-mono text-xs text-red-600 font-semibold">{trade.sl_price?.toFixed(2) ?? "&mdash;"}</td>
              <td className="px-5 py-2.5 font-mono text-xs">{trade.rpt_amount ? formatINR.format(trade.rpt_amount) : "&mdash;"}</td>
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
  );
}

// ---------------------------------------------------------------------------
// WatchlistSection (READY stocks)
// ---------------------------------------------------------------------------

export function WatchlistSection({
  readyStocks,
  loading,
}: {
  readyStocks: WatchlistItem[];
  loading: boolean;
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200">
      <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
        <h3 className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
          READY Stocks — Watching for Entry
        </h3>
        <Link href="/pipeline" className="text-[11px] text-teal-600 hover:text-teal-700 font-medium">
          Open Pipeline &rarr;
        </Link>
      </div>
      {loading ? (
        <div className="p-5 space-y-2">
          <Skeleton className="h-8 w-full bg-slate-100" />
          <Skeleton className="h-8 w-full bg-slate-100" />
        </div>
      ) : readyStocks.length === 0 ? (
        <div className="p-8 text-center">
          <p className="text-sm text-slate-400">No READY stocks yet. Run a scan first.</p>
          <Link href="/pipeline" className="text-xs text-teal-600 hover:text-teal-700 mt-1 inline-block">
            Go to Pipeline to scan &rarr;
          </Link>
        </div>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[11px] text-slate-400 uppercase tracking-wider border-b border-slate-100">
              <th className="px-5 py-2 font-medium">Symbol</th>
              <th className="px-5 py-2 font-medium">Stage</th>
              <th className="px-5 py-2 font-medium">Trigger Level</th>
              <th className="px-5 py-2 font-medium">SL%</th>
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
                  {stock.trigger_level != null ? formatINR.format(stock.trigger_level) : "&mdash;"}
                </td>
                <td className="px-5 py-2.5 font-mono text-xs text-red-600">
                  {stock.planned_sl_pct != null ? `${stock.planned_sl_pct}%` : "&mdash;"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ActionsCTA
// ---------------------------------------------------------------------------

export function ActionsCTA() {
  return (
    <div className="bg-teal-50 border border-teal-200 rounded-xl p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-sm font-semibold text-teal-800 mb-1">
            Ready to enter? Use the Actions page.
          </h3>
          <p className="text-xs text-teal-700 leading-relaxed">
            In the last 30 minutes of market (3:00-3:30 PM), go to <strong>Actions</strong> and click{" "}
            <strong>Refresh Prices</strong>. If any READY stock has crossed its trigger, a buy signal
            will appear — with position size already calculated. Click Act to open the trade.
          </p>
        </div>
        <Link
          href="/actions"
          className="shrink-0 text-[11px] font-semibold px-3 py-2 rounded-lg border border-teal-400 bg-white text-teal-700 hover:bg-teal-100 transition-colors whitespace-nowrap"
        >
          Go to Actions &rarr;
        </Link>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// PostMarketLinks
// ---------------------------------------------------------------------------

export function PostMarketLinks({
  nearCount,
  readyCount,
  stance,
}: {
  nearCount: number;
  readyCount: number;
  stance: MarketStance | null;
}) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Link href="/pipeline" className="block">
        <div className="bg-white rounded-xl border border-slate-200 p-5 hover:border-teal-300 transition-colors">
          <h3 className="text-sm font-semibold text-slate-800 mb-1">Run Scans</h3>
          <p className="text-xs text-slate-400">
            PPC, NPC, Contraction — results auto-fill your pipeline ({nearCount} NEAR, {readyCount} READY)
          </p>
        </div>
      </Link>
      <Link href="/actions" className="block">
        <div className="bg-white rounded-xl border border-slate-200 p-5 hover:border-teal-300 transition-colors">
          <h3 className="text-sm font-semibold text-slate-800 mb-1">Check Signals</h3>
          <p className="text-xs text-slate-400">Refresh prices to see BUY/SELL alerts with position sizing</p>
        </div>
      </Link>
      <Link href="/review" className="block">
        <div className="bg-white rounded-xl border border-slate-200 p-5 hover:border-teal-300 transition-colors">
          <h3 className="text-sm font-semibold text-slate-800 mb-1">Weekly Review</h3>
          <p className="text-xs text-slate-400">
            {stance ? `Stance: ${stance.stance}` : "Log stance + journal"}
          </p>
        </div>
      </Link>
    </div>
  );
}
