"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  getLearningProgress,
  type LearningProgress,
} from "@/lib/intelligence-api";
import { ErrorBoundary } from "@/components/error-boundary";
import {
  LoopStatusBanner,
  SummaryCards,
  FeedbackLoopDiagram,
  LoadingSkeleton,
} from "./components/learning-charts";
import {
  ParameterGrid,
  ExperimentTimeline,
} from "./components/parameter-grid";

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
