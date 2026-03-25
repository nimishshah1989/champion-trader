"use client";

import Link from "next/link";
import {
  type RegimeData,
  type RegimeType,
  type OptimizeStatus,
  type RiskStatus,
  type SetupCard,
} from "@/lib/intelligence-api";
import { Skeleton } from "@/components/ui/skeleton";
import { safeFixed, safeFormatINR } from "@/lib/format";

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

// ---------------------------------------------------------------------------
// RegimeCard
// ---------------------------------------------------------------------------

export function RegimeCard({ regime, loading }: { regime: RegimeData | null; loading: boolean }) {
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

  const FALLBACK_CONFIG = { label: regime.regime ?? "Unknown", color: "text-slate-700", bg: "bg-slate-50", border: "border-slate-200" };
  const config = REGIME_CONFIG[regime.regime] ?? FALLBACK_CONFIG;

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
          <span className="ml-1 font-mono font-semibold text-slate-700">{safeFixed(regime.adx, 1)}</span>
        </div>
        <div>
          <span className="text-slate-400">VIX</span>
          <span className="ml-1 font-mono font-semibold text-slate-700">{safeFixed(regime.vix, 2)}</span>
        </div>
        <div>
          <span className="text-slate-400">Hurst</span>
          <span className="ml-1 font-mono font-semibold text-slate-700">{safeFixed(regime.hurst, 3)}</span>
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

// ---------------------------------------------------------------------------
// OptimizeCard
// ---------------------------------------------------------------------------

export function OptimizeCard({ status, loading }: { status: OptimizeStatus | null; loading: boolean }) {
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
      {status.current_best_score != null && (
        <p className="text-[10px] text-slate-400 mt-1">
          Best score: <span className="font-mono font-semibold text-teal-600">{safeFixed(status.current_best_score, 2)}</span>
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

// ---------------------------------------------------------------------------
// RiskCard
// ---------------------------------------------------------------------------

export function RiskCard({ risk, loading }: { risk: RiskStatus | null; loading: boolean }) {
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

  const totalRisk = risk.total_risk_pct ?? 0;
  const riskColor = totalRisk > 8 ? "text-red-600" : totalRisk > 5 ? "text-amber-600" : "text-emerald-600";

  return (
    <div className={`bg-white rounded-xl border ${risk.frozen ? "border-red-200" : "border-slate-200"} p-5`}>
      <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">Risk Status</p>
      <div className="flex items-baseline gap-2">
        <span className={`text-3xl font-bold font-mono ${riskColor}`}>
          {safeFixed(risk.total_risk_pct, 1)}%
        </span>
        <span className="text-xs text-slate-400">/ {risk.max_risk_pct ?? 10}% max</span>
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

// ---------------------------------------------------------------------------
// SetupCardComponent
// ---------------------------------------------------------------------------

export function SetupCardComponent({
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
          <span className="ml-1 font-mono font-semibold text-teal-600">{safeFixed(setup.score, 1)}</span>
        </div>
        <div>
          <span className="text-slate-400">Entry</span>
          <span className="ml-1 font-mono font-semibold text-slate-700">{safeFormatINR(setup.entry_price)}</span>
        </div>
        <div>
          <span className="text-slate-400">SL</span>
          <span className="ml-1 font-mono font-semibold text-red-600">{safeFormatINR(setup.stop_loss)}</span>
        </div>
        <div>
          <span className="text-slate-400">Target</span>
          <span className="ml-1 font-mono font-semibold text-emerald-600">{safeFormatINR(setup.target)}</span>
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
