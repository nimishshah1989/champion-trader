"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  getRegime,
  getOptimizeStatus,
  getDailyBrief,
  getRiskStatus,
  classifyRegimeNow,
  generateBriefNow,
  type RegimeData,
  type OptimizeStatus,
  type DailyBrief,
  type RiskStatus,
} from "@/lib/intelligence-api";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorBoundary } from "@/components/error-boundary";
import {
  RegimeCard,
  OptimizeCard,
  RiskCard,
  SetupCardComponent,
} from "./components/dashboard-cards";

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
  const [classifying, setClassifying] = useState(false);
  const [generatingBrief, setGeneratingBrief] = useState(false);

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
    } catch (err) {
      console.error("Failed to fetch intelligence dashboard data:", err);
      setError("Failed to load intelligence data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  async function handleClassifyNow() {
    setClassifying(true);
    try {
      const result = await classifyRegimeNow();
      setRegime(result);
    } catch (err) {
      console.error("Regime classification failed:", err);
    } finally {
      setClassifying(false);
    }
  }

  async function handleGenerateBrief() {
    setGeneratingBrief(true);
    try {
      const result = await generateBriefNow();
      setBrief(result);
      // Reload full brief with setups
      const fullBrief = await getDailyBrief().catch(() => null);
      if (fullBrief) setBrief(fullBrief);
    } catch (err) {
      console.error("Brief generation failed:", err);
    } finally {
      setGeneratingBrief(false);
    }
  }

  function handleApprove(symbol: string) {
    console.log("Approved:", symbol);
  }

  function handleSkip(symbol: string) {
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
      <ErrorBoundary>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-800 uppercase tracking-wider">Market Regime</h2>
            <button
              onClick={handleClassifyNow}
              disabled={classifying}
              className="text-[11px] font-medium text-teal-600 hover:text-teal-700 disabled:text-slate-400 transition-colors"
            >
              {classifying ? "Classifying..." : "Classify Now"}
            </button>
          </div>
          <div className="grid gap-4 md:grid-cols-4">
            <RegimeCard regime={regime} loading={loading} />
            <OptimizeCard status={optimizeStatus} loading={loading} />
            <RiskCard risk={risk} loading={loading} />
          </div>
        </div>
      </ErrorBoundary>

      {/* Daily Brief */}
      <ErrorBoundary>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
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
            <button
              onClick={handleGenerateBrief}
              disabled={generatingBrief}
              className="text-[11px] font-medium text-teal-600 hover:text-teal-700 disabled:text-slate-400 transition-colors"
            >
              {generatingBrief ? "Generating..." : "Generate Now"}
            </button>
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
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-6">
              <p className="text-sm font-medium text-slate-600">No daily brief yet</p>
              <p className="text-xs text-slate-400 mt-1">
                The CIO Agent generates a brief automatically at 17:00 IST every trading day.
                Once Kite auth is set up and the bar store is populated, click &ldquo;Generate Now&rdquo; to trigger it manually.
              </p>
            </div>
          )}
        </div>
      </ErrorBoundary>

      {/* Top Setups */}
      <ErrorBoundary>
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
      </ErrorBoundary>

      {/* Quick links */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Link href="/intelligence/learning" className="block">
          <div className="bg-teal-50 rounded-xl border border-teal-200 p-5 hover:border-teal-400 transition-colors">
            <h3 className="text-sm font-semibold text-teal-800 mb-1">Learning Dashboard</h3>
            <p className="text-xs text-teal-600">See how the system learns: parameter evolution, feedback loop health</p>
          </div>
        </Link>
        <Link href="/intelligence/learning" className="block">
          <div className="bg-white rounded-xl border border-slate-200 p-5 hover:border-teal-300 transition-colors">
            <h3 className="text-sm font-semibold text-slate-800 mb-1">Parameter Evolution</h3>
            <p className="text-xs text-slate-400">View strategy parameter evolution, experiment timeline, loop health</p>
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
