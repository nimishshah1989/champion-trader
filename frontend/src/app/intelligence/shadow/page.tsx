"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  getShadowComparison,
  type ShadowComparison,
  type ShadowTrade,
} from "@/lib/intelligence-api";
import { Skeleton } from "@/components/ui/skeleton";
import { formatINR, safeFixed, safeFormatINR } from "@/lib/format";

const LAKH = 1_00_000;
const CRORE = 1_00_00_000;

function formatPnl(value: number): string {
  if (Math.abs(value) >= CRORE) return `${(value / CRORE).toFixed(2)} Cr`;
  if (Math.abs(value) >= LAKH) return `${(value / LAKH).toFixed(2)} L`;
  return formatINR.format(value);
}

function rColor(v: number | null): string {
  if (v === null) return "text-slate-400";
  return v >= 0 ? "text-emerald-600" : "text-red-600";
}

function winRateColor(rate: number): string {
  return rate >= 50 ? "text-emerald-600" : "text-red-600";
}

function SummaryCards({ data, loading }: { data: ShadowComparison | null; loading: boolean }) {
  if (loading) {
    return (
      <div className="grid gap-4 md:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-white rounded-xl border border-slate-200 p-5">
            <Skeleton className="h-4 w-20 bg-slate-100 mb-2" />
            <Skeleton className="h-9 w-16 bg-slate-100" />
          </div>
        ))}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
        <p className="text-sm text-slate-400">No shadow portfolio data available.</p>
        <p className="text-xs text-slate-400 mt-1">The shadow portfolio tracks all signals regardless of approval status.</p>
      </div>
    );
  }

  const alphaPositive = data.human_alpha >= 0;

  return (
    <div className="grid gap-4 md:grid-cols-4">
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">Shadow Win Rate</p>
        <span className={`text-3xl font-bold font-mono ${winRateColor(data.shadow_win_rate)}`}>
          {safeFixed(data.shadow_win_rate, 1)}%
        </span>
        <p className="text-[10px] text-slate-400 mt-1">Avg R: {(data.shadow_avg_r ?? 0) >= 0 ? "+" : ""}{safeFixed(data.shadow_avg_r, 2)}R</p>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">Live Win Rate</p>
        <span className={`text-3xl font-bold font-mono ${winRateColor(data.live_win_rate)}`}>
          {safeFixed(data.live_win_rate, 1)}%
        </span>
        <p className="text-[10px] text-slate-400 mt-1">Avg R: {(data.live_avg_r ?? 0) >= 0 ? "+" : ""}{safeFixed(data.live_avg_r, 2)}R</p>
      </div>

      <div className={`rounded-xl border p-5 ${alphaPositive ? "bg-emerald-50 border-emerald-200" : "bg-red-50 border-red-200"}`}>
        <p className="text-xs text-slate-500 font-medium uppercase tracking-wide mb-1">Human Alpha</p>
        <span className={`text-3xl font-bold font-mono ${alphaPositive ? "text-emerald-600" : "text-red-600"}`}>
          {alphaPositive ? "+" : ""}{safeFixed(data.human_alpha, 2)}R
        </span>
        <p className="text-[10px] text-slate-500 mt-1">Live vs shadow difference</p>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">Verdict</p>
        <p className="text-sm font-semibold text-slate-800 leading-snug mt-1">{data.verdict}</p>
      </div>
    </div>
  );
}

function BreakdownCards({ data, loading }: { data: ShadowComparison | null; loading: boolean }) {
  if (loading) {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        {[1, 2].map((i) => (
          <div key={i} className="bg-white rounded-xl border border-slate-200 p-5">
            <Skeleton className="h-4 w-32 bg-slate-100 mb-2" />
            <Skeleton className="h-9 w-20 bg-slate-100" />
          </div>
        ))}
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">Approved Setups Win Rate</p>
        <span className={`text-3xl font-bold font-mono ${winRateColor(data.approved_win_rate)}`}>
          {safeFixed(data.approved_win_rate, 1)}%
        </span>
        <p className="text-[10px] text-slate-400 mt-1">Signals you chose to trade</p>
      </div>
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">Skipped Setups Win Rate</p>
        <span className={`text-3xl font-bold font-mono ${data.skipped_win_rate >= 50 ? "text-emerald-600" : "text-amber-600"}`}>
          {safeFixed(data.skipped_win_rate, 1)}%
        </span>
        <p className="text-[10px] text-slate-400 mt-1">Signals you passed on</p>
      </div>
    </div>
  );
}

function ShadowTradesTable({ trades, loading }: { trades: ShadowTrade[]; loading: boolean }) {
  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2">
        {[1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} className="h-8 w-full bg-slate-100" />
        ))}
      </div>
    );
  }

  if (trades.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
        <p className="text-sm text-slate-400">No shadow trades recorded yet.</p>
        <p className="text-xs text-slate-400 mt-1">Trades appear here once the CIO Agent generates setup signals.</p>
      </div>
    );
  }

  const TH = "px-5 py-2 font-medium";

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="px-5 py-3 border-b border-slate-100">
        <h3 className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
          Shadow Trades ({trades.length})
        </h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[11px] text-slate-400 uppercase tracking-wider border-b border-slate-100">
              <th className={TH}>Date</th>
              <th className={TH}>Symbol</th>
              <th className={TH}>Signal Type</th>
              <th className={TH}>Score</th>
              <th className={TH}>Entry</th>
              <th className={TH}>Stop</th>
              <th className={TH}>Target</th>
              <th className={TH}>Status</th>
              <th className={TH}>Paper Exit</th>
              <th className={TH}>Paper R</th>
              <th className={TH}>Paper P&amp;L</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((trade) => (
              <tr key={trade.id} className="border-b border-slate-50 hover:bg-slate-50/50">
                <td className="px-5 py-2.5 text-xs text-slate-500 whitespace-nowrap">
                  {new Date(trade.signal_date).toLocaleDateString("en-IN", { day: "2-digit", month: "short" })}
                </td>
                <td className="px-5 py-2.5 font-bold text-slate-800">{trade.symbol}</td>
                <td className="px-5 py-2.5">
                  <span className="bg-blue-50 text-blue-700 border border-blue-200 rounded-full px-2 py-0.5 text-[10px] font-medium">
                    {trade.signal_type}
                  </span>
                </td>
                <td className="px-5 py-2.5 font-mono text-xs font-semibold text-teal-600">{safeFixed(trade.score, 1)}</td>
                <td className="px-5 py-2.5 font-mono text-xs">{safeFormatINR(trade.entry)}</td>
                <td className="px-5 py-2.5 font-mono text-xs text-red-600">{safeFormatINR(trade.stop)}</td>
                <td className="px-5 py-2.5 font-mono text-xs text-emerald-600">{safeFormatINR(trade.target)}</td>
                <td className="px-5 py-2.5">
                  {trade.was_approved ? (
                    <span className="bg-emerald-50 text-emerald-700 rounded-full px-2 py-0.5 text-[10px] font-semibold">Approved</span>
                  ) : (
                    <span className="bg-slate-100 text-slate-500 rounded-full px-2 py-0.5 text-[10px] font-semibold">Skipped</span>
                  )}
                </td>
                <td className="px-5 py-2.5 font-mono text-xs">
                  {trade.paper_exit === null
                    ? <span className="text-amber-600 font-medium">Pending</span>
                    : formatINR.format(trade.paper_exit)}
                </td>
                <td className={`px-5 py-2.5 font-mono text-xs font-semibold ${rColor(trade.paper_r)}`}>
                  {trade.paper_r !== null ? `${trade.paper_r >= 0 ? "+" : ""}${trade.paper_r.toFixed(2)}R` : "Pending"}
                </td>
                <td className={`px-5 py-2.5 font-mono text-xs font-semibold ${rColor(trade.paper_pnl)}`}>
                  {trade.paper_pnl !== null ? formatPnl(trade.paper_pnl) : "Pending"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function ShadowPage() {
  const [data, setData] = useState<ShadowComparison | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [result] = await Promise.allSettled([getShadowComparison()]);
      if (result.status === "fulfilled") {
        setData(result.value);
      } else {
        setError("Failed to load shadow portfolio data.");
      }
    } catch {
      setError("Failed to load shadow portfolio data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div className="space-y-6">
      {/* Header with breadcrumb */}
      <div>
        <div className="flex items-center gap-2 mb-0.5">
          <Link href="/intelligence" className="text-xs text-teal-600 hover:text-teal-700 font-medium">
            Intelligence
          </Link>
          <span className="text-xs text-slate-300">/</span>
          <span className="text-xs text-slate-500">Shadow Portfolio</span>
        </div>
        <h1 className="text-xl font-semibold text-slate-800">Shadow Portfolio</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Compare shadow (all signals) vs live (approved only) -- measure human alpha
        </p>
      </div>

      {/* Error banner */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Summary comparison cards: Shadow WR, Live WR, Human Alpha, Verdict */}
      <SummaryCards data={data} loading={loading} />

      {/* Approved vs Skipped breakdown */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-slate-800 uppercase tracking-wider">Approval Breakdown</h2>
        <BreakdownCards data={data} loading={loading} />
      </div>

      {/* Shadow trades table */}
      <ShadowTradesTable trades={data?.trades ?? []} loading={loading} />
    </div>
  );
}
