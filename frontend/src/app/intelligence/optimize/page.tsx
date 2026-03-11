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
  type ExperimentRecord,
  type StrategyParameter,
} from "@/lib/intelligence-api";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const OUTCOME_STYLES: Record<string, { color: string; bg: string }> = {
  KEEP: { color: "text-emerald-700", bg: "bg-emerald-50" },
  REVERT: { color: "text-red-700", bg: "bg-red-50" },
};

type SortField = "timestamp" | "parameter" | "old_score" | "new_score" | "outcome";
type SortDirection = "asc" | "desc";

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SummaryCards({
  status,
  history,
  loading,
}: {
  status: OptimizeStatus | null;
  history: OptimizeHistory | null;
  loading: boolean;
}) {
  if (loading) {
    return (
      <div className="grid gap-4 md:grid-cols-5">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="bg-white rounded-xl border border-slate-200 p-5">
            <Skeleton className="h-4 w-20 bg-slate-100 mb-2" />
            <Skeleton className="h-9 w-16 bg-slate-100" />
          </div>
        ))}
      </div>
    );
  }

  const totalExperiments = history?.total_experiments ?? status?.total_experiments ?? 0;
  const keepRate = history?.keep_rate ?? (status ? (status.keep_count / Math.max(status.total_experiments, 1)) * 100 : 0);
  const bestScore = history?.best_score ?? status?.current_best_score ?? 0;
  const mostImproved = history?.most_improved_parameter ?? "--";

  return (
    <div className="grid gap-4 md:grid-cols-5">
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">Status</p>
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${status?.running ? "bg-emerald-500 animate-pulse" : "bg-slate-300"}`}
          />
          <span className="text-lg font-bold text-slate-800">
            {status?.running ? "Running" : "Stopped"}
          </span>
        </div>
        {status?.last_run && (
          <p className="text-[10px] text-slate-400 mt-1">
            Last run: {new Date(status.last_run).toLocaleString("en-IN")}
          </p>
        )}
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">Total Experiments</p>
        <span className="text-3xl font-bold text-slate-800 font-mono">{totalExperiments}</span>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">Keep Rate</p>
        <span className={`text-3xl font-bold font-mono ${keepRate >= 50 ? "text-emerald-600" : "text-amber-600"}`}>
          {keepRate.toFixed(0)}%
        </span>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">Best Score</p>
        <span className="text-3xl font-bold font-mono text-teal-600">{bestScore.toFixed(2)}</span>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">Most Improved</p>
        <span className="text-lg font-bold text-slate-800 break-all">{mostImproved}</span>
      </div>
    </div>
  );
}

function ExperimentTable({
  experiments,
  loading,
  sortField,
  sortDirection,
  onSort,
}: {
  experiments: ExperimentRecord[];
  loading: boolean;
  sortField: SortField;
  sortDirection: SortDirection;
  onSort: (field: SortField) => void;
}) {
  const headerClass = "px-5 py-2 font-medium cursor-pointer hover:text-slate-600 select-none";

  function renderSortArrow(field: SortField) {
    if (sortField !== field) return null;
    return <span className="ml-1">{sortDirection === "asc" ? "\u25B2" : "\u25BC"}</span>;
  }

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2">
        {[1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} className="h-8 w-full bg-slate-100" />
        ))}
      </div>
    );
  }

  if (experiments.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
        <p className="text-sm text-slate-400">No experiments recorded yet.</p>
        <p className="text-xs text-slate-400 mt-1">Start AutoOptimize to begin running experiments.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="px-5 py-3 border-b border-slate-100">
        <h3 className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
          Experiment History
        </h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[11px] text-slate-400 uppercase tracking-wider border-b border-slate-100">
              <th className={headerClass} onClick={() => onSort("timestamp")}>
                Timestamp{renderSortArrow("timestamp")}
              </th>
              <th className={headerClass} onClick={() => onSort("parameter")}>
                Parameter{renderSortArrow("parameter")}
              </th>
              <th className="px-5 py-2 font-medium">Old &rarr; New</th>
              <th className="px-5 py-2 font-medium">Hypothesis</th>
              <th className={headerClass} onClick={() => onSort("old_score")}>
                Old Score{renderSortArrow("old_score")}
              </th>
              <th className={headerClass} onClick={() => onSort("new_score")}>
                New Score{renderSortArrow("new_score")}
              </th>
              <th className={headerClass} onClick={() => onSort("outcome")}>
                Outcome{renderSortArrow("outcome")}
              </th>
            </tr>
          </thead>
          <tbody>
            {experiments.map((exp) => {
              const outcomeStyle = OUTCOME_STYLES[exp.outcome] ?? { color: "text-slate-600", bg: "bg-slate-50" };
              const scoreDelta = exp.new_score - exp.old_score;
              const deltaColor = scoreDelta > 0 ? "text-emerald-600" : scoreDelta < 0 ? "text-red-600" : "text-slate-500";

              return (
                <tr key={exp.id} className="border-b border-slate-50 hover:bg-slate-50/50">
                  <td className="px-5 py-2.5 text-xs text-slate-500 whitespace-nowrap">
                    {new Date(exp.timestamp).toLocaleString("en-IN", {
                      day: "2-digit",
                      month: "short",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </td>
                  <td className="px-5 py-2.5 font-mono text-xs font-semibold text-slate-800">
                    {exp.parameter}
                  </td>
                  <td className="px-5 py-2.5 font-mono text-xs">
                    <span className="text-slate-500">{exp.old_value.toFixed(3)}</span>
                    <span className="text-slate-300 mx-1">&rarr;</span>
                    <span className="text-slate-800 font-semibold">{exp.new_value.toFixed(3)}</span>
                  </td>
                  <td className="px-5 py-2.5 text-xs text-slate-600 max-w-xs truncate">
                    {exp.hypothesis}
                  </td>
                  <td className="px-5 py-2.5 font-mono text-xs text-slate-600">
                    {exp.old_score.toFixed(2)}
                  </td>
                  <td className="px-5 py-2.5 font-mono text-xs">
                    <span className="text-slate-800 font-semibold">{exp.new_score.toFixed(2)}</span>
                    <span className={`ml-1 text-[10px] ${deltaColor}`}>
                      ({scoreDelta >= 0 ? "+" : ""}{scoreDelta.toFixed(2)})
                    </span>
                  </td>
                  <td className="px-5 py-2.5">
                    <span
                      className={`${outcomeStyle.bg} ${outcomeStyle.color} rounded-full px-2 py-0.5 text-[10px] font-semibold`}
                    >
                      {exp.outcome}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ParameterTable({
  parameters,
  loading,
}: {
  parameters: StrategyParameter[];
  loading: boolean;
}) {
  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-6 w-full bg-slate-100" />
        ))}
      </div>
    );
  }

  if (parameters.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
        <p className="text-sm text-slate-400">No strategy parameters loaded.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="px-5 py-3 border-b border-slate-100">
        <h3 className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
          Current Parameters & Bounds
        </h3>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-[11px] text-slate-400 uppercase tracking-wider border-b border-slate-100">
            <th className="px-5 py-2 font-medium">Parameter</th>
            <th className="px-5 py-2 font-medium">Current Value</th>
            <th className="px-5 py-2 font-medium">Min</th>
            <th className="px-5 py-2 font-medium">Max</th>
            <th className="px-5 py-2 font-medium">Description</th>
          </tr>
        </thead>
        <tbody>
          {parameters.map((param) => {
            const range = param.max_bound - param.min_bound;
            const position = range > 0 ? ((param.value - param.min_bound) / range) * 100 : 50;

            return (
              <tr key={param.name} className="border-b border-slate-50 hover:bg-slate-50/50">
                <td className="px-5 py-2.5 font-mono text-xs font-semibold text-slate-800">
                  {param.name}
                </td>
                <td className="px-5 py-2.5">
                  <span className="font-mono text-xs font-bold text-teal-600">
                    {param.value.toFixed(3)}
                  </span>
                  {/* Visual position indicator */}
                  <div className="mt-1 h-1 bg-slate-100 rounded-full w-20 overflow-hidden">
                    <div
                      className="h-full bg-teal-500 rounded-full"
                      style={{ width: `${Math.min(Math.max(position, 2), 98)}%` }}
                    />
                  </div>
                </td>
                <td className="px-5 py-2.5 font-mono text-xs text-slate-500">{param.min_bound.toFixed(3)}</td>
                <td className="px-5 py-2.5 font-mono text-xs text-slate-500">{param.max_bound.toFixed(3)}</td>
                <td className="px-5 py-2.5 text-xs text-slate-600 max-w-xs">{param.description}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

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
    } catch {
      // Individual failures handled by allSettled
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
      <SummaryCards status={status} history={history} loading={loading} />

      {/* Experiment history table */}
      <ExperimentTable
        experiments={sortedExperiments}
        loading={loading}
        sortField={sortField}
        sortDirection={sortDirection}
        onSort={handleSort}
      />

      {/* Parameter evolution */}
      <ParameterTable parameters={parameters} loading={loading} />
    </div>
  );
}
