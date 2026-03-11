"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  getRegime,
  getOptimizeStatus,
  getDailyBrief,
  getRiskStatus,
  type RegimeData,
  type RegimeType,
  type OptimizeStatus,
  type DailyBrief,
  type RiskStatus,
  type SetupCard,
} from "@/lib/intelligence-api";
import { Skeleton } from "@/components/ui/skeleton";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const REGIME_CONFIG: Record<
  RegimeType,
  { label: string; color: string; bg: string; border: string }
> = {
  TRENDING_BULL: {
    label: "Trending Bull",
    color: "text-emerald-700",
    bg: "bg-emerald-50",
    border: "border-emerald-200",
  },
  RANGING_QUIET: {
    label: "Ranging Quiet",
    color: "text-amber-700",
    bg: "bg-amber-50",
    border: "border-amber-200",
  },
  HIGH_VOLATILITY: {
    label: "High Volatility",
    color: "text-orange-700",
    bg: "bg-orange-50",
    border: "border-orange-200",
  },
  WEAKENING_BEAR: {
    label: "Weakening Bear",
    color: "text-red-700",
    bg: "bg-red-50",
    border: "border-red-200",
  },
};

const formatINR = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 2,
});

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function RegimeCard({ regime, loading }: { regime: RegimeData | null; loading: boolean }) {
  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-5 col-span-2">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-2">Market Regime</p>
        <Skeleton className="h-10 w-40 bg-slate-100" />
        <div className="flex gap-6 mt-3">
          <Skeleton className="h-4 w-20 bg-slate-100" />
          <Skeleton className="h-4 w-20 bg-slate-100" />
          <Skeleton className="h-4 w-20 bg-slate-100" />
        </div>
      </div>
    );
  }

  if (!regime) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-5 col-span-2">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">Market Regime</p>
        <span className="text-3xl font-bold text-slate-300">--</span>
        <p className="text-[10px] text-slate-400 mt-1">No regime data available yet</p>
      </div>
    );
  }

  const config = REGIME_CONFIG[regime.regime];

  return (
    <div className={`bg-white rounded-xl border ${config.border} p-5 col-span-2`}>
      <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">Market Regime</p>
      <div className="flex items-center gap-3">
        <span className={`${config.bg} ${config.color} rounded-lg px-3 py-1.5 text-sm font-bold`}>
          {config.label}
        </span>
      </div>
      <div className="flex gap-6 mt-3 text-xs">
        <div>
          <span className="text-slate-400">ADX</span>
          <span className="ml-1 font-mono font-semibold text-slate-700">{regime.adx.toFixed(1)}</span>
        </div>
        <div>
          <span className="text-slate-400">VIX</span>
          <span className="ml-1 font-mono font-semibold text-slate-700">{regime.vix.toFixed(2)}</span>
        </div>
        <div>
          <span className="text-slate-400">Hurst</span>
          <span className="ml-1 font-mono font-semibold text-slate-700">{regime.hurst.toFixed(3)}</span>
        </div>
      </div>
      {regime.timestamp && (
        <p className="text-[10px] text-slate-400 mt-2">
          Updated: {new Date(regime.timestamp).toLocaleString("en-IN")}
        </p>
      )}
    </div>
  );
}

function OptimizeCard({ status, loading }: { status: OptimizeStatus | null; loading: boolean }) {
  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-2">AutoOptimize</p>
        <Skeleton className="h-9 w-20 bg-slate-100" />
        <Skeleton className="h-4 w-32 bg-slate-100 mt-2" />
      </div>
    );
  }

  if (!status) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">AutoOptimize</p>
        <span className="text-3xl font-bold text-slate-300">--</span>
        <p className="text-[10px] text-slate-400 mt-1">Not connected</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">AutoOptimize</p>
      <div className="flex items-center gap-2">
        <span
          className={`w-2 h-2 rounded-full ${status.running ? "bg-emerald-500 animate-pulse" : "bg-slate-300"}`}
        />
        <span className="text-lg font-bold text-slate-800">
          {status.running ? "Running" : "Stopped"}
        </span>
      </div>
      {status.current_best_score !== null && (
        <p className="text-[10px] text-slate-400 mt-1">
          Best score: <span className="font-mono font-semibold text-teal-600">{status.current_best_score.toFixed(2)}</span>
        </p>
      )}
      <p className="text-[10px] text-slate-400 mt-0.5">
        {status.total_experiments} experiments | {status.keep_count} kept
      </p>
      <Link
        href="/intelligence/optimize"
        className="text-[10px] text-teal-600 hover:text-teal-700 mt-1 block font-medium"
      >
        View history &rarr;
      </Link>
    </div>
  );
}

function RiskCard({ risk, loading }: { risk: RiskStatus | null; loading: boolean }) {
  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-2">Risk Status</p>
        <Skeleton className="h-9 w-20 bg-slate-100" />
        <Skeleton className="h-4 w-32 bg-slate-100 mt-2" />
      </div>
    );
  }

  if (!risk) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">Risk Status</p>
        <span className="text-3xl font-bold text-slate-300">--</span>
        <p className="text-[10px] text-slate-400 mt-1">No risk data</p>
      </div>
    );
  }

  const riskColor = risk.total_risk_pct > 8 ? "text-red-600" : risk.total_risk_pct > 5 ? "text-amber-600" : "text-emerald-600";

  return (
    <div className={`bg-white rounded-xl border ${risk.frozen ? "border-red-200" : "border-slate-200"} p-5`}>
      <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">Risk Status</p>
      <div className="flex items-baseline gap-2">
        <span className={`text-3xl font-bold font-mono ${riskColor}`}>
          {risk.total_risk_pct.toFixed(1)}%
        </span>
        <span className="text-xs text-slate-400">/ {risk.max_risk_pct}% max</span>
      </div>
      <p className="text-[10px] text-slate-400 mt-1">
        {risk.open_positions} open position{risk.open_positions !== 1 ? "s" : ""}
      </p>
      {risk.frozen && (
        <div className="mt-2 bg-red-50 border border-red-200 rounded-lg px-3 py-1.5">
          <span className="text-[11px] font-semibold text-red-700">FROZEN</span>
          {risk.frozen_reason && (
            <p className="text-[10px] text-red-600 mt-0.5">{risk.frozen_reason}</p>
          )}
        </div>
      )}
    </div>
  );
}

function SetupCardComponent({
  setup,
  onApprove,
  onSkip,
}: {
  setup: SetupCard;
  onApprove: (symbol: string) => void;
  onSkip: (symbol: string) => void;
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 hover:border-slate-300 transition-colors">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-bold text-slate-800 tracking-wide">{setup.symbol}</span>
        <span className="bg-blue-50 text-blue-700 border border-blue-200 rounded-full px-2 py-0.5 text-[10px] font-medium">
          {setup.signal_type}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs mb-2">
        <div>
          <span className="text-slate-400">Score</span>
          <span className="ml-1 font-mono font-semibold text-teal-600">{setup.score.toFixed(1)}</span>
        </div>
        <div>
          <span className="text-slate-400">Entry</span>
          <span className="ml-1 font-mono font-semibold text-slate-700">{formatINR.format(setup.entry_price)}</span>
        </div>
        <div>
          <span className="text-slate-400">SL</span>
          <span className="ml-1 font-mono font-semibold text-red-600">{formatINR.format(setup.stop_loss)}</span>
        </div>
        <div>
          <span className="text-slate-400">Target</span>
          <span className="ml-1 font-mono font-semibold text-emerald-600">{formatINR.format(setup.target)}</span>
        </div>
      </div>
      {setup.rationale && (
        <p className="text-[10px] text-slate-500 mb-3 leading-relaxed">{setup.rationale}</p>
      )}
      <div className="flex items-center gap-2 pt-3 border-t border-slate-100">
        <button
          onClick={() => onApprove(setup.symbol)}
          className="text-[11px] font-medium px-3 py-1 rounded border border-teal-200 bg-teal-50 text-teal-700 hover:bg-teal-100 transition-colors"
        >
          Approve
        </button>
        <button
          onClick={() => onSkip(setup.symbol)}
          className="text-[11px] font-medium px-3 py-1 rounded border border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100 transition-colors"
        >
          Skip
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function IntelligenceDashboard() {
  const [regime, setRegime] = useState<RegimeData | null>(null);
  const [optimizeStatus, setOptimizeStatus] = useState<OptimizeStatus | null>(null);
  const [brief, setBrief] = useState<DailyBrief | null>(null);
  const [risk, setRisk] = useState<RiskStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    try {
      const [regimeResult, optimizeResult, briefResult, riskResult] = await Promise.allSettled([
        getRegime(),
        getOptimizeStatus(),
        getDailyBrief(),
        getRiskStatus(),
      ]);

      if (regimeResult.status === "fulfilled") setRegime(regimeResult.value);
      if (optimizeResult.status === "fulfilled") setOptimizeStatus(optimizeResult.value);
      if (briefResult.status === "fulfilled") setBrief(briefResult.value);
      if (riskResult.status === "fulfilled") setRisk(riskResult.value);
    } catch {
      setError("Failed to load intelligence data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  function handleApprove(symbol: string) {
    // Placeholder — will POST to approval endpoint
    console.log("Approved:", symbol);
  }

  function handleSkip(symbol: string) {
    // Placeholder — will POST to skip endpoint
    console.log("Skipped:", symbol);
  }

  const topSetups = brief?.top_setups?.slice(0, 3) ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-slate-800">Intelligence Dashboard</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          CTS Intelligence Engine -- regime, optimization, setups, and risk at a glance
        </p>
      </div>

      {/* Error banner */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Top row: Regime + Optimize + Risk */}
      <div className="grid gap-4 md:grid-cols-4">
        <RegimeCard regime={regime} loading={loading} />
        <OptimizeCard status={optimizeStatus} loading={loading} />
        <RiskCard risk={risk} loading={loading} />
      </div>

      {/* Daily Brief */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-slate-800 uppercase tracking-wider">Daily Brief</h2>
          {brief?.date && (
            <span className="text-[10px] text-slate-400 bg-slate-100 rounded-full px-2 py-0.5 font-medium">
              {new Date(brief.date).toLocaleDateString("en-IN", {
                day: "numeric",
                month: "short",
                year: "numeric",
              })}
            </span>
          )}
        </div>

        {loading ? (
          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2">
            <Skeleton className="h-4 w-full bg-slate-100" />
            <Skeleton className="h-4 w-3/4 bg-slate-100" />
            <Skeleton className="h-4 w-5/6 bg-slate-100" />
            <Skeleton className="h-4 w-2/3 bg-slate-100" />
          </div>
        ) : brief?.brief_text ? (
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <pre className="text-sm text-slate-700 whitespace-pre-wrap font-sans leading-relaxed">
              {brief.brief_text}
            </pre>
            {brief.generated_at && (
              <p className="text-[10px] text-slate-400 mt-3 pt-3 border-t border-slate-100">
                Generated: {new Date(brief.generated_at).toLocaleString("en-IN")}
              </p>
            )}
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
            <p className="text-sm text-slate-400">No daily brief available.</p>
            <p className="text-xs text-slate-400 mt-1">
              The CIO Agent generates briefs during the overnight research loop.
            </p>
          </div>
        )}
      </div>

      {/* Top Setups */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-800 uppercase tracking-wider">Top Setups</h2>
          <Link
            href="/intelligence/shadow"
            className="text-[11px] text-teal-600 hover:text-teal-700 font-medium"
          >
            Shadow Portfolio &rarr;
          </Link>
        </div>

        {loading ? (
          <div className="grid gap-4 md:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white rounded-xl border border-slate-200 p-4 space-y-3">
                <Skeleton className="h-5 w-24 bg-slate-100" />
                <Skeleton className="h-4 w-32 bg-slate-100" />
                <Skeleton className="h-4 w-full bg-slate-100" />
                <Skeleton className="h-8 w-28 bg-slate-100" />
              </div>
            ))}
          </div>
        ) : topSetups.length > 0 ? (
          <div className="grid gap-4 md:grid-cols-3">
            {topSetups.map((setup) => (
              <SetupCardComponent
                key={setup.symbol}
                setup={setup}
                onApprove={handleApprove}
                onSkip={handleSkip}
              />
            ))}
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
            <p className="text-sm text-slate-400">No setups recommended today.</p>
            <p className="text-xs text-slate-400 mt-1">Run the scanner post-market to generate setups.</p>
          </div>
        )}
      </div>

      {/* Quick links */}
      <div className="grid gap-4 md:grid-cols-3">
        <Link href="/intelligence/optimize" className="block">
          <div className="bg-white rounded-xl border border-slate-200 p-5 hover:border-teal-300 transition-colors">
            <h3 className="text-sm font-semibold text-slate-800 mb-1">AutoOptimize History</h3>
            <p className="text-xs text-slate-400">View experiments, parameter evolution, and keep/revert history</p>
          </div>
        </Link>
        <Link href="/intelligence/shadow" className="block">
          <div className="bg-white rounded-xl border border-slate-200 p-5 hover:border-teal-300 transition-colors">
            <h3 className="text-sm font-semibold text-slate-800 mb-1">Shadow Portfolio</h3>
            <p className="text-xs text-slate-400">Compare shadow vs live performance and measure human alpha</p>
          </div>
        </Link>
        <Link href="/intelligence/attribution" className="block">
          <div className="bg-white rounded-xl border border-slate-200 p-5 hover:border-teal-300 transition-colors">
            <h3 className="text-sm font-semibold text-slate-800 mb-1">Signal Attribution</h3>
            <p className="text-xs text-slate-400">Win rates by signal type and regime breakdown</p>
          </div>
        </Link>
      </div>
    </div>
  );
}
