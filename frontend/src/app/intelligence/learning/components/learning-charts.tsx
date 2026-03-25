"use client";

import { type LearningProgress } from "@/lib/intelligence-api";
import { Skeleton } from "@/components/ui/skeleton";
import { safeFixed } from "@/lib/format";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const REGIME_COLORS: Record<string, { text: string; bg: string; border: string }> = {
  TRENDING_BULL: { text: "text-emerald-700", bg: "bg-emerald-50", border: "border-emerald-200" },
  RANGING_QUIET: { text: "text-slate-700", bg: "bg-slate-50", border: "border-slate-200" },
  HIGH_VOLATILITY: { text: "text-amber-700", bg: "bg-amber-50", border: "border-amber-200" },
  WEAKENING_BEAR: { text: "text-red-700", bg: "bg-red-50", border: "border-red-200" },
};

const TREND_LABELS: Record<string, { label: string; color: string }> = {
  improving: { label: "Improving", color: "text-emerald-600" },
  stable: { label: "Starting", color: "text-slate-500" },
  plateau: { label: "Plateau", color: "text-amber-600" },
};

// ---------------------------------------------------------------------------
// LoopStatusBanner
// ---------------------------------------------------------------------------

export function LoopStatusBanner({ data }: { data: LearningProgress }) {
  const { loop_status } = data;
  const isClosed = loop_status.closed;

  return (
    <div
      className={`rounded-xl border p-5 ${
        isClosed
          ? "bg-emerald-50 border-emerald-200"
          : "bg-amber-50 border-amber-200"
      }`}
    >
      <div className="flex items-start gap-3">
        <div
          className={`w-3 h-3 rounded-full mt-1 flex-shrink-0 ${
            isClosed ? "bg-emerald-500 animate-pulse" : "bg-amber-500"
          }`}
        />
        <div>
          <h3
            className={`text-sm font-semibold ${
              isClosed ? "text-emerald-800" : "text-amber-800"
            }`}
          >
            {isClosed ? "Learning Loop Active" : "Learning Loop Not Started"}
          </h3>
          <p
            className={`text-xs mt-1 ${
              isClosed ? "text-emerald-700" : "text-amber-700"
            }`}
          >
            {loop_status.description}
          </p>
          {loop_status.issues.length > 0 && (
            <ul className="mt-2 space-y-1">
              {loop_status.issues.map((issue, i) => (
                <li key={i} className="text-xs text-amber-700">
                  &bull; {issue}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// SummaryCards
// ---------------------------------------------------------------------------

export function SummaryCards({ data }: { data: LearningProgress }) {
  const { experiment_summary: s, learning_velocity: v, current_regime: r } = data;
  const regimeStyle = REGIME_COLORS[r.regime] ?? REGIME_COLORS.RANGING_QUIET;
  const trendInfo = TREND_LABELS[v.trend] ?? TREND_LABELS.stable;

  return (
    <div className="grid gap-3 grid-cols-2 md:grid-cols-3 lg:grid-cols-5">
      {/* Regime */}
      <div className={`rounded-xl border p-5 ${regimeStyle.bg} ${regimeStyle.border}`}>
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">
          Current Regime
        </p>
        <span className={`text-lg font-bold ${regimeStyle.text}`}>
          {r.regime.replace(/_/g, " ")}
        </span>
        <p className="text-[10px] text-slate-500 mt-1">
          ADX {safeFixed(r.nifty_adx, 1)} &middot; VIX {safeFixed(r.india_vix, 1)}
        </p>
      </div>

      {/* Total Experiments */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">
          Experiments Run
        </p>
        <span className="text-3xl font-bold text-slate-800 font-mono">
          {s.total_experiments}
        </span>
      </div>

      {/* Keep Rate */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">
          Keep Rate
        </p>
        <span
          className={`text-3xl font-bold font-mono ${
            s.keep_rate_pct >= 50 ? "text-emerald-600" : "text-amber-600"
          }`}
        >
          {safeFixed(s.keep_rate_pct, 0)}%
        </span>
        <p className="text-[10px] text-slate-400 mt-1">
          {s.keep_count} kept / {s.revert_count} reverted
        </p>
      </div>

      {/* Best Score */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">
          Best Score
        </p>
        <span className="text-3xl font-bold font-mono text-teal-600">
          {safeFixed(s.best_score, 2)}
        </span>
        {s.latest_score != null && (
          <p className="text-[10px] text-slate-400 mt-1">
            Latest: {safeFixed(s.latest_score, 2)}
          </p>
        )}
      </div>

      {/* Learning Trend */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">
          Learning Trend
        </p>
        <span className={`text-lg font-bold ${trendInfo.color}`}>
          {trendInfo.label}
        </span>
        <p className="text-[10px] text-slate-400 mt-1">
          Recent keep: {safeFixed(v.recent_keep_rate, 0)}%
          {v.older_keep_rate != null && ` (prev: ${safeFixed(v.older_keep_rate, 0)}%)`}
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// FeedbackLoopDiagram
// ---------------------------------------------------------------------------

export function FeedbackLoopDiagram() {
  const steps = [
    { label: "AutoOptimize", desc: "Runs experiments overnight", icon: "1" },
    { label: "strategy.py", desc: "Parameters updated", icon: "2" },
    { label: "Regime Classifier", desc: "Adjusts for market regime", icon: "3" },
    { label: "Signal Agent", desc: "Filters & scores setups", icon: "4" },
    { label: "Backtest Engine", desc: "Validates with historical data", icon: "5" },
    { label: "Results", desc: "Feed back to next experiment", icon: "6" },
  ];

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <h3 className="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-4">
        How the Learning Loop Works
      </h3>
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-3 justify-items-center">
        {steps.map((step, idx) => (
          <div key={idx} className="flex flex-col items-center">
            <div className="w-10 h-10 rounded-full bg-teal-50 border-2 border-teal-200 flex items-center justify-center">
              <span className="text-sm font-bold text-teal-600">
                {step.icon}
              </span>
            </div>
            <p className="text-[10px] font-semibold text-slate-700 mt-1 text-center">
              {step.label}
            </p>
            <p className="text-[9px] text-slate-400 text-center">
              {step.desc}
            </p>
          </div>
        ))}
        {/* Loop arrow back */}
        <div className="w-full text-center mt-1">
          <span className="text-[10px] text-teal-500 font-medium">
            &larr; Results feed back into next AutoOptimize cycle &rarr;
          </span>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

export function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="h-20 bg-slate-100 rounded-xl animate-pulse" />
      <div className="grid gap-4 md:grid-cols-5">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="bg-white rounded-xl border border-slate-200 p-5">
            <Skeleton className="h-4 w-20 bg-slate-100 mb-2" />
            <Skeleton className="h-9 w-16 bg-slate-100" />
          </div>
        ))}
      </div>
      <Skeleton className="h-64 w-full bg-slate-100 rounded-xl" />
      <Skeleton className="h-48 w-full bg-slate-100 rounded-xl" />
    </div>
  );
}
