"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { getAttribution, type AttributionRow } from "@/lib/intelligence-api";
import { Skeleton } from "@/components/ui/skeleton";
import { safeFixed } from "@/lib/format";

// ---------------------------------------------------------------------------
// Constants & Helpers
// ---------------------------------------------------------------------------

type SortField = "signal_type" | "regime" | "trade_count" | "win_count" | "win_rate" | "avg_r" | "total_r";
type SortDir = "asc" | "desc";

const REGIME_CFG: Record<string, { label: string; color: string; bg: string; border: string }> = {
  TRENDING_BULL: { label: "Trending Bull", color: "text-emerald-700", bg: "bg-emerald-50", border: "border-emerald-200" },
  RANGING_QUIET: { label: "Ranging Quiet", color: "text-amber-700", bg: "bg-amber-50", border: "border-amber-200" },
  HIGH_VOLATILITY: { label: "High Volatility", color: "text-orange-700", bg: "bg-orange-50", border: "border-orange-200" },
  WEAKENING_BEAR: { label: "Weakening Bear", color: "text-red-700", bg: "bg-red-50", border: "border-red-200" },
};
const REGIME_ORDER = ["TRENDING_BULL", "RANGING_QUIET", "HIGH_VOLATILITY", "WEAKENING_BEAR"];

function rl(regime: string) { return REGIME_CFG[regime]?.label ?? regime.replace(/_/g, " "); }
function wrColor(r: number) { return r >= 60 ? "text-emerald-600" : r >= 40 ? "text-amber-600" : "text-red-600"; }
function wrBg(r: number) { return r >= 60 ? "bg-emerald-50" : r >= 40 ? "bg-amber-50" : "bg-red-50"; }
function wrBorder(r: number) { return r >= 60 ? "border-emerald-200" : r >= 40 ? "border-amber-200" : "border-red-200"; }
function rCfg(regime: string) { return REGIME_CFG[regime] ?? { bg: "bg-slate-100", color: "text-slate-600" }; }
function signR(v: number | null | undefined) { if (v == null) return "--"; return v >= 0 ? `+${v.toFixed(2)}R` : `${v.toFixed(2)}R`; }

// ---------------------------------------------------------------------------
// Summary Cards
// ---------------------------------------------------------------------------

function SummaryCards({ rows, loading }: { rows: AttributionRow[]; loading: boolean }) {
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
  if (rows.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
        <p className="text-sm text-slate-400">No attribution data available yet.</p>
        <p className="text-xs text-slate-400 mt-1">Generated from closed trades with signal and regime labels.</p>
      </div>
    );
  }

  const totalTrades = rows.reduce((s, r) => s + r.trade_count, 0);
  const totalWins = rows.reduce((s, r) => s + r.win_count, 0);
  const wr = totalTrades > 0 ? (totalWins / totalTrades) * 100 : 0;
  const totalR = rows.reduce((s, r) => s + r.total_r, 0);

  const bySignal = new Map<string, { t: number; w: number }>();
  for (const row of rows) {
    const p = bySignal.get(row.signal_type) ?? { t: 0, w: 0 };
    bySignal.set(row.signal_type, { t: p.t + row.trade_count, w: p.w + row.win_count });
  }
  let bestSig = "--", bestWr = 0;
  for (const [sig, s] of bySignal) {
    const rate = s.t > 0 ? (s.w / s.t) * 100 : 0;
    if (rate > bestWr) { bestWr = rate; bestSig = sig; }
  }

  return (
    <div className="grid gap-4 md:grid-cols-4">
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">Total Signals</p>
        <span className="text-3xl font-bold text-slate-800 font-mono">{totalTrades}</span>
        <p className="text-[10px] text-slate-400 mt-1">{rows.length} signal-regime combinations</p>
      </div>
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">Overall Win Rate</p>
        <span className={`text-3xl font-bold font-mono ${wrColor(wr)}`}>{safeFixed(wr, 1)}%</span>
        <p className="text-[10px] text-slate-400 mt-1">{totalWins} wins / {totalTrades} trades</p>
      </div>
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">Best Signal Type</p>
        <span className="text-lg font-bold text-teal-600">{bestSig}</span>
        <p className="text-[10px] text-slate-400 mt-1">
          <span className={`font-mono font-semibold ${wrColor(bestWr)}`}>{safeFixed(bestWr, 1)}%</span> win rate
        </p>
      </div>
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-1">Cumulative R</p>
        <span className={`text-3xl font-bold font-mono ${totalR >= 0 ? "text-emerald-600" : "text-red-600"}`}>
          {totalR >= 0 ? "+" : ""}{safeFixed(totalR, 1)}R
        </span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Attribution Matrix (Heatmap)
// ---------------------------------------------------------------------------

function AttributionMatrix({ rows, loading }: { rows: AttributionRow[]; loading: boolean }) {
  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
        <Skeleton className="h-4 w-32 bg-slate-100" />
        <div className="grid grid-cols-5 gap-3">
          {Array.from({ length: 15 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full bg-slate-100 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }
  if (rows.length === 0) return null;

  const signals = [...new Set(rows.map((r) => r.signal_type))].sort();
  const presentRegimes = new Set(rows.map((r) => r.regime));
  const regimes = REGIME_ORDER.filter((r) => presentRegimes.has(r));
  for (const r of presentRegimes) { if (!REGIME_ORDER.includes(r)) regimes.push(r); }

  const lookup = new Map<string, AttributionRow>();
  for (const row of rows) lookup.set(`${row.signal_type}__${row.regime}`, row);

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="px-5 py-3 border-b border-slate-100">
        <h3 className="text-xs font-semibold text-slate-600 uppercase tracking-wider">Attribution Matrix</h3>
        <p className="text-[10px] text-slate-400 mt-0.5">Win rate by signal type and market regime</p>
      </div>
      <div className="p-5 overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr>
              <th className="px-3 py-2 text-left text-[11px] text-slate-400 font-medium uppercase tracking-wider w-36">
                Signal / Regime
              </th>
              {regimes.map((reg) => {
                const c = rCfg(reg);
                return (
                  <th key={reg} className="px-3 py-2 text-center">
                    <span className={`inline-block rounded-full px-2.5 py-0.5 text-[10px] font-semibold ${c.bg} ${c.color}`}>
                      {rl(reg)}
                    </span>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {signals.map((sig) => (
              <tr key={sig} className="border-t border-slate-100">
                <td className="px-3 py-3">
                  <span className="bg-blue-50 text-blue-700 border border-blue-200 rounded-full px-2.5 py-0.5 text-[10px] font-semibold">
                    {sig}
                  </span>
                </td>
                {regimes.map((reg) => {
                  const cell = lookup.get(`${sig}__${reg}`);
                  if (!cell) return (
                    <td key={reg} className="px-3 py-3 text-center">
                      <div className="bg-slate-50 rounded-lg px-3 py-2 border border-slate-100">
                        <span className="text-xs text-slate-300 font-mono">--</span>
                      </div>
                    </td>
                  );
                  return (
                    <td key={reg} className="px-3 py-3 text-center">
                      <div className={`${wrBg(cell.win_rate)} rounded-lg px-3 py-2 border ${wrBorder(cell.win_rate)}`}>
                        <span className={`text-base font-bold font-mono ${wrColor(cell.win_rate)}`}>
                          {safeFixed(cell.win_rate, 0)}%
                        </span>
                        <div className="flex items-center justify-center gap-2 mt-1">
                          <span className="text-[10px] text-slate-500">{cell.trade_count} trades</span>
                          <span className={`text-[10px] font-mono font-semibold ${cell.avg_r >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                            {signR(cell.avg_r)}
                          </span>
                        </div>
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Detailed Table
// ---------------------------------------------------------------------------

function DetailedTable({ rows, loading, sortField, sortDir, onSort }: {
  rows: AttributionRow[]; loading: boolean; sortField: SortField; sortDir: SortDir; onSort: (f: SortField) => void;
}) {
  const hc = "px-5 py-2 font-medium cursor-pointer hover:text-slate-600 select-none";
  const arrow = (f: SortField) => sortField !== f ? null : <span className="ml-1">{sortDir === "asc" ? "\u25B2" : "\u25BC"}</span>;

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2">
        {[1, 2, 3, 4, 5, 6].map((i) => <Skeleton key={i} className="h-8 w-full bg-slate-100" />)}
      </div>
    );
  }
  if (rows.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
        <p className="text-sm text-slate-400">No attribution data available yet.</p>
        <p className="text-xs text-slate-400 mt-1">Generated from closed trades with signal type and regime labels.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="px-5 py-3 border-b border-slate-100">
        <h3 className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
          Detailed Breakdown ({rows.length} rows)
        </h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[11px] text-slate-400 uppercase tracking-wider border-b border-slate-100">
              <th className={hc} onClick={() => onSort("signal_type")}>Signal Type{arrow("signal_type")}</th>
              <th className={hc} onClick={() => onSort("regime")}>Regime{arrow("regime")}</th>
              <th className={hc} onClick={() => onSort("trade_count")}>Trades{arrow("trade_count")}</th>
              <th className={hc} onClick={() => onSort("win_count")}>Wins{arrow("win_count")}</th>
              <th className={hc} onClick={() => onSort("win_rate")}>Win Rate{arrow("win_rate")}</th>
              <th className={hc} onClick={() => onSort("avg_r")}>Avg R{arrow("avg_r")}</th>
              <th className={hc} onClick={() => onSort("total_r")}>Total R{arrow("total_r")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => {
              const c = rCfg(row.regime);
              return (
                <tr key={`${row.signal_type}-${row.regime}-${idx}`} className="border-b border-slate-50 hover:bg-slate-50/50">
                  <td className="px-5 py-2.5">
                    <span className="bg-blue-50 text-blue-700 border border-blue-200 rounded-full px-2 py-0.5 text-[10px] font-semibold">
                      {row.signal_type}
                    </span>
                  </td>
                  <td className="px-5 py-2.5">
                    <span className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold ${c.bg} ${c.color}`}>
                      {rl(row.regime)}
                    </span>
                  </td>
                  <td className="px-5 py-2.5 font-mono text-xs text-slate-700">{row.trade_count}</td>
                  <td className="px-5 py-2.5 font-mono text-xs text-slate-700">{row.win_count}</td>
                  <td className="px-5 py-2.5">
                    <span className={`${wrBg(row.win_rate)} ${wrColor(row.win_rate)} rounded px-2 py-0.5 font-mono text-xs font-bold`}>
                      {safeFixed(row.win_rate, 1)}%
                    </span>
                  </td>
                  <td className={`px-5 py-2.5 font-mono text-xs font-semibold ${row.avg_r >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                    {signR(row.avg_r)}
                  </td>
                  <td className={`px-5 py-2.5 font-mono text-xs font-semibold ${row.total_r >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                    {(row.total_r ?? 0) >= 0 ? "+" : ""}{safeFixed(row.total_r, 1)}R
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

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function AttributionPage() {
  const [rows, setRows] = useState<AttributionRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortField, setSortField] = useState<SortField>("win_rate");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const fetchData = useCallback(async () => {
    try {
      const [result] = await Promise.allSettled([getAttribution()]);
      if (result.status === "fulfilled") setRows(result.value);
    } catch {
      // Attribution data not available yet
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  function handleSort(field: SortField) {
    if (sortField === field) setSortDir((p) => (p === "asc" ? "desc" : "asc"));
    else { setSortField(field); setSortDir("desc"); }
  }

  const sorted = [...rows].sort((a, b) => {
    const d = sortDir === "asc" ? 1 : -1;
    switch (sortField) {
      case "signal_type": return d * a.signal_type.localeCompare(b.signal_type);
      case "regime": return d * a.regime.localeCompare(b.regime);
      case "trade_count": return d * (a.trade_count - b.trade_count);
      case "win_count": return d * (a.win_count - b.win_count);
      case "win_rate": return d * (a.win_rate - b.win_rate);
      case "avg_r": return d * (a.avg_r - b.avg_r);
      case "total_r": return d * (a.total_r - b.total_r);
      default: return 0;
    }
  });

  return (
    <div className="space-y-6">
      {/* Breadcrumb + Header */}
      <div>
        <div className="flex items-center gap-2 mb-0.5">
          <Link href="/intelligence" className="text-xs text-teal-600 hover:text-teal-700 font-medium">
            Intelligence
          </Link>
          <span className="text-xs text-slate-300">/</span>
          <span className="text-xs text-slate-500">Attribution</span>
        </div>
        <h1 className="text-xl font-semibold text-slate-800">Signal Attribution</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Win rates broken down by signal type and market regime -- identify what works where
        </p>
      </div>

      <SummaryCards rows={rows} loading={loading} />
      <AttributionMatrix rows={rows} loading={loading} />
      <DetailedTable rows={sorted} loading={loading} sortField={sortField} sortDir={sortDir} onSort={handleSort} />
    </div>
  );
}
