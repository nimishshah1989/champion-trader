"use client";

import Link from "next/link";
import { type LearningProgress } from "@/lib/intelligence-api";
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

// ---------------------------------------------------------------------------
// ParameterGrid
// ---------------------------------------------------------------------------

export function ParameterGrid({ data }: { data: LearningProgress }) {
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

// ---------------------------------------------------------------------------
// ExperimentTimeline
// ---------------------------------------------------------------------------

export function ExperimentTimeline({ data }: { data: LearningProgress }) {
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
