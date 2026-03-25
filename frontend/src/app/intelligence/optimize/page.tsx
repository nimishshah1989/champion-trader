"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  getOptimizeStatus,
  getOptimizeHistory,
  getStrategyParameters,
  startOptimize,
  stopOptimize,
  type OptimizeStatus,
  type OptimizeHistory,
  type StrategyParameter,
} from "@/lib/intelligence-api";
import { toast } from "sonner";
import { ErrorBoundary } from "@/components/error-boundary";
import {
  SummaryCards,
  ExperimentTable,
  ParameterTable,
  type SortField,
  type SortDirection,
} from "./components/experiment-table";

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function OptimizePage() {
  const [status, setStatus] = useState<OptimizeStatus | null>(null);
  const [history, setHistory] = useState<OptimizeHistory | null>(null);
  const [parameters, setParameters] = useState<StrategyParameter[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [sortField, setSortField] = useState<SortField>("timestamp");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  const fetchAll = useCallback(async () => {
    try {
      const [statusResult, historyResult, paramsResult] = await Promise.allSettled([
        getOptimizeStatus(),
        getOptimizeHistory(),
        getStrategyParameters(),
      ]);

      if (statusResult.status === "fulfilled") setStatus(statusResult.value);
      if (historyResult.status === "fulfilled") setHistory(historyResult.value);
      if (paramsResult.status === "fulfilled") setParameters(paramsResult.value);
    } catch (err) {
      console.error("Failed to fetch optimize data:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  async function handleStart() {
    setActionLoading(true);
    try {
      await startOptimize();
      toast.success("AutoOptimize started");
      await fetchAll();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to start";
      toast.error(message);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleStop() {
    setActionLoading(true);
    try {
      await stopOptimize();
      toast.success("AutoOptimize stopped");
      await fetchAll();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to stop";
      toast.error(message);
    } finally {
      setActionLoading(false);
    }
  }

  function handleSort(field: SortField) {
    if (sortField === field) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
  }

  // Sort experiments
  const sortedExperiments = [...(history?.experiments ?? [])].sort((a, b) => {
    const dir = sortDirection === "asc" ? 1 : -1;
    switch (sortField) {
      case "timestamp":
        return dir * (new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
      case "parameter":
        return dir * a.parameter.localeCompare(b.parameter);
      case "old_score":
        return dir * (a.old_score - b.old_score);
      case "new_score":
        return dir * (a.new_score - b.new_score);
      case "outcome":
        return dir * a.outcome.localeCompare(b.outcome);
      default:
        return 0;
    }
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-0.5">
            <Link href="/intelligence" className="text-xs text-teal-600 hover:text-teal-700 font-medium">
              Intelligence
            </Link>
            <span className="text-xs text-slate-300">/</span>
            <span className="text-xs text-slate-500">AutoOptimize</span>
          </div>
          <h1 className="text-xl font-semibold text-slate-800">AutoOptimize</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Overnight parameter research loop -- Karpathy-style gradient-free optimization
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleStart}
            disabled={actionLoading || (status?.running ?? false)}
            className="bg-teal-600 text-white font-medium px-4 py-2 rounded-lg hover:bg-teal-700 transition-colors text-sm disabled:opacity-50"
          >
            Start
          </button>
          <button
            onClick={handleStop}
            disabled={actionLoading || !(status?.running ?? false)}
            className="bg-white text-slate-600 font-medium px-4 py-2 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors text-sm disabled:opacity-50"
          >
            Stop
          </button>
        </div>
      </div>

      {/* Summary stats */}
      <ErrorBoundary>
        <SummaryCards status={status} history={history} loading={loading} />
      </ErrorBoundary>

      {/* Experiment history table */}
      <ErrorBoundary>
        <ExperimentTable
          experiments={sortedExperiments}
          loading={loading}
          sortField={sortField}
          sortDirection={sortDirection}
          onSort={handleSort}
        />
      </ErrorBoundary>

      {/* Parameter evolution */}
      <ErrorBoundary>
        <ParameterTable parameters={parameters} loading={loading} />
      </ErrorBoundary>
    </div>
  );
}
