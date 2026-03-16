"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  getLearningProgress,
  type LearningProgress,
} from "@/lib/intelligence-api";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorBoundary } from "@/components/error-boundary";
import { safeFixed } from "@/lib/format";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PARAM_LABELS: Record<string, string> = {
  ppc_trp_ratio_min: "PPC TRP Ratio Min",
  ppc_close_position_min: "PPC Close Position Min",
  ppc_volume_ratio_min: "PPC Volume Ratio Min",
  npc_trp_ratio_min: "NPC TRP Ratio Min",
  npc_close_position_max: "NPC Close Position Max",
  npc_volume_ratio_min: "NPC Volume Ratio Min",
  contraction_atr_lookback: "Contraction ATR Lookback",
  contraction_narrowing_min: "Contraction Narrowing Min",
  contraction_resistance_pct: "Contraction Resistance %",
  min_base_days: "Min Base Days",
  sma_window: "SMA Window",
  stage_sma_lookback: "Stage SMA Lookback",
  min_adt_crore: "Min ADT (Cr)",
  weight_ppc: "Weight: PPC",
  weight_contraction: "Weight: Contraction",
  weight_npc_filter: "Weight: NPC Filter",
};

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
// Sub-components
// ---------------------------------------------------------------------------

function LoopStatusBanner({ data }: { data: LearningProgress }) {
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

function SummaryCards({ data }: { data: LearningProgress }) {
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

function ParameterGrid({ data }: { data: LearningProgress }) {
  const params = data.parameters;
  const entries = Object.entries(params);

  // Group by category
  const ppcParams = entries.filter(([k]) => k.startsWith("ppc_"));
  const npcParams = entries.filter(([k]) => k.startsWith("npc_"));
  const contractionParams = entries.filter(([k]) => k.startsWith("contraction_"));
  const otherParams = entries.filter(
    ([k]) =>
      !k.startsWith("ppc_") &&
      !k.startsWith("npc_") &&
      !k.startsWith("contraction_") &&
      !k.startsWith("weight_")
  );
  const weightParams = entries.filter(([k]) => k.startsWith("weight_"));

  const groups = [
    { label: "PPC Signal Thresholds", params: ppcParams },
    { label: "NPC Signal Thresholds", params: npcParams },
    { label: "Contraction Thresholds", params: contractionParams },
    { label: "Base & Liquidity", params: otherParams },
    { label: "Composite Weights", params: weightParams },
  ];

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="px-5 py-3 border-b border-slate-100">
        <h3 className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
          Live Parameters — Base + Regime Adjustments
        </h3>
      </div>
      <div className="divide-y divide-slate-100">
        {groups.map((group) => (
          <div key={group.label}>
            <div className="px-5 py-2 bg-slate-50/50">
              <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                {group.label}
              </span>
            </div>
            {group.params.map(([key, p]) => {
              const range = p.bound_high - p.bound_low;
              const pct = range > 0 ? ((p.effective_value - p.bound_low) / range) * 100 : 50;

              return (
                <div
                  key={key}
                  className="px-4 py-3 flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 hover:bg-slate-50/50"
                >
                  <div className="sm:w-40 md:w-48 flex-shrink-0">
                    <p className="text-xs font-semibold text-slate-700">
                      {PARAM_LABELS[key] ?? key.replace(/_/g, " ")}
                    </p>
                    {p.regime_adjusted && (
                      <span className="text-[9px] text-amber-600 font-medium">
                        REGIME-ADJUSTED
                      </span>
                    )}
                  </div>

                  {/* Value + bar */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono text-[10px] sm:text-xs text-slate-400">
                        {safeFixed(p.bound_low, 2)}
                      </span>
                      <span
                        className={`font-mono text-xs sm:text-sm font-bold ${
                          p.regime_adjusted ? "text-amber-600" : "text-teal-600"
                        }`}
                      >
                        {safeFixed(p.effective_value, 3)}
                      </span>
                      <span className="font-mono text-[10px] sm:text-xs text-slate-400">
                        {safeFixed(p.bound_high, 2)}
                      </span>
                    </div>
                    <div className="h-2 bg-slate-100 rounded-full overflow-hidden relative">
                      {/* Base value marker */}
                      {p.regime_adjusted && (
                        <div
                          className="absolute top-0 h-full w-0.5 bg-slate-400 z-10"
                          style={{
                            left: `${Math.min(
                              Math.max(
                                ((p.base_value - p.bound_low) / range) * 100,
                                1
                              ),
                              99
                            )}%`,
                          }}
                        />
                      )}
                      <div
                        className={`h-full rounded-full ${
                          p.regime_adjusted ? "bg-amber-400" : "bg-teal-500"
                        }`}
                        style={{
                          width: `${Math.min(Math.max(pct, 2), 98)}%`,
                        }}
                      />
                    </div>
                  </div>

                  {/* Experiment stats */}
                  <div className="sm:w-28 flex-shrink-0 sm:text-right">
                    <span className="text-xs text-slate-500">
                      {p.experiments_run} exp
                    </span>
                    {p.improvements > 0 && (
                      <span className="text-xs text-emerald-600 ml-1">
                        ({p.improvements} kept)
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

function ExperimentTimeline({ data }: { data: LearningProgress }) {
  const timeline = data.experiment_timeline;

  if (timeline.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
        <p className="text-sm text-slate-400">
          No experiments recorded yet.
        </p>
        <p className="text-xs text-slate-400 mt-1">
          Start AutoOptimize to begin the learning loop.
        </p>
        <Link
          href="/intelligence/optimize"
          className="inline-block mt-3 text-xs text-teal-600 hover:text-teal-700 font-medium"
        >
          Go to AutoOptimize &rarr;
        </Link>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
        <h3 className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
          Recent Experiments
        </h3>
        <Link
          href="/intelligence/optimize"
          className="text-xs text-teal-600 hover:text-teal-700 font-medium"
        >
          View all &rarr;
        </Link>
      </div>
      <div className="divide-y divide-slate-50 max-h-96 overflow-y-auto">
        {[...timeline].reverse().map((item, idx) => {
          const isKeep = item.outcome === "KEEP";
          const delta = item.score_delta;

          return (
            <div
              key={idx}
              className="px-5 py-3 flex items-center gap-3 hover:bg-slate-50/50"
            >
              <div
                className={`w-2 h-2 rounded-full flex-shrink-0 ${
                  isKeep ? "bg-emerald-500" : "bg-red-400"
                }`}
              />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-slate-700">
                  <span className="font-mono font-semibold">
                    {item.parameter}
                  </span>
                  <span
                    className={`ml-2 text-[10px] font-semibold rounded-full px-1.5 py-0.5 ${
                      isKeep
                        ? "bg-emerald-50 text-emerald-700"
                        : "bg-red-50 text-red-700"
                    }`}
                  >
                    {item.outcome}
                  </span>
                </p>
              </div>
              {delta != null && (
                <span
                  className={`text-xs font-mono ${
                    delta > 0
                      ? "text-emerald-600"
                      : delta < 0
                        ? "text-red-600"
                        : "text-slate-400"
                  }`}
                >
                  {delta >= 0 ? "+" : ""}
                  {safeFixed(delta, 3)}
                </span>
              )}
              <span className="text-[10px] text-slate-400 flex-shrink-0">
                {item.timestamp
                  ? new Date(item.timestamp).toLocaleString("en-IN", {
                      day: "2-digit",
                      month: "short",
                      hour: "2-digit",
                      minute: "2-digit",
                    })
                  : ""}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function FeedbackLoopDiagram() {
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

function LoadingSkeleton() {
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

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function LearningDashboardPage() {
  const [data, setData] = useState<LearningProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const result = await getLearningProgress();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchData, 30_000);
    return () => clearInterval(interval);
  }, [fetchData]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-0.5">
          <Link
            href="/intelligence"
            className="text-xs text-teal-600 hover:text-teal-700 font-medium"
          >
            Intelligence
          </Link>
          <span className="text-xs text-slate-300">/</span>
          <span className="text-xs text-slate-500">Learning Dashboard</span>
        </div>
        <h1 className="text-xl font-semibold text-slate-800">
          Learning Dashboard
        </h1>
        <p className="text-sm text-slate-500 mt-0.5">
          See how the system learns: parameter evolution, experiment outcomes,
          and feedback loop health.
        </p>
      </div>

      {loading && <LoadingSkeleton />}

      {error && !data && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-5">
          <p className="text-sm text-red-700">{error}</p>
          <button
            onClick={fetchData}
            className="mt-2 text-xs text-red-600 hover:text-red-700 font-medium"
          >
            Retry
          </button>
        </div>
      )}

      {data && (
        <>
          {/* Loop health banner */}
          <ErrorBoundary>
            <LoopStatusBanner data={data} />
          </ErrorBoundary>

          {/* Summary cards */}
          <ErrorBoundary>
            <SummaryCards data={data} />
          </ErrorBoundary>

          {/* How it works diagram */}
          <ErrorBoundary>
            <FeedbackLoopDiagram />
          </ErrorBoundary>

          {/* Two-column: Parameters + Timeline */}
          <div className="grid gap-6 grid-cols-1 lg:grid-cols-5">
            <div className="lg:col-span-3">
              <ErrorBoundary>
                <ParameterGrid data={data} />
              </ErrorBoundary>
            </div>
            <div className="lg:col-span-2">
              <ErrorBoundary>
                <ExperimentTimeline data={data} />
              </ErrorBoundary>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
