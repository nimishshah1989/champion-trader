"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getRsStrategyStatus,
  getRsStrategyTrades,
  runRsStrategyNow,
  type RsPortfolioStatus,
  type RsStrategyTrade,
  type RsBothPortfolios,
  type RsAllTrades,
} from "@/lib/api";
import { toast } from "sonner";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmt(n: number, decimals = 0): string {
  return new Intl.NumberFormat("en-IN", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(n);
}

function fmtPct(n: number | null | undefined): string {
  if (n == null) return "—";
  const sign = n >= 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}%`;
}

function colorPct(n: number | null | undefined): string {
  if (n == null) return "text-slate-500";
  return n >= 0 ? "text-emerald-600" : "text-red-600";
}

function isFullStatus(p: RsBothPortfolios["A"]): p is RsPortfolioStatus {
  return !("error" in p);
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatCard({
  label,
  value,
  sub,
  valueClass,
}: {
  label: string;
  value: string;
  sub?: string;
  valueClass?: string;
}) {
  return (
    <div className="rounded-xl border bg-white px-5 py-4 shadow-sm">
      <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">{label}</p>
      <p className={`mt-1 text-xl font-semibold ${valueClass ?? "text-slate-800"}`}>{value}</p>
      {sub && <p className="mt-0.5 text-xs text-slate-400">{sub}</p>}
    </div>
  );
}

function ExitBadge({ reason }: { reason: string | null }) {
  if (!reason) return null;
  const cls =
    reason === "STOP_LOSS"
      ? "bg-red-100 text-red-700"
      : reason === "RS_DEATH_CROSS"
      ? "bg-orange-100 text-orange-700"
      : "bg-slate-100 text-slate-600";
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {reason === "STOP_LOSS" ? "Stop Loss" : reason === "RS_DEATH_CROSS" ? "Death Cross" : reason}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Single portfolio panel
// ---------------------------------------------------------------------------

function PortfolioPanel({
  label,
  status,
  trades,
  activeTab,
  onTabChange,
}: {
  label: "A" | "B";
  status: RsBothPortfolios["A"] | null;
  trades: RsStrategyTrade[];
  activeTab: "open" | "closed";
  onTabChange: (t: "open" | "closed") => void;
}) {
  const color = label === "A" ? "indigo" : "violet";
  const borderColor = label === "A" ? "border-indigo-200" : "border-violet-200";
  const headerBg = label === "A" ? "bg-indigo-50" : "bg-violet-50";
  const headerText = label === "A" ? "text-indigo-700" : "text-violet-700";

  if (!status) {
    return (
      <div className={`rounded-xl border ${borderColor} bg-white shadow-sm overflow-hidden`}>
        <div className={`px-5 py-3 ${headerBg} flex items-center gap-2`}>
          <span className={`text-sm font-semibold ${headerText}`}>Portfolio {label}</span>
        </div>
        <div className="px-5 py-8 text-center text-sm text-slate-400">Loading…</div>
      </div>
    );
  }

  if (!isFullStatus(status)) {
    return (
      <div className={`rounded-xl border ${borderColor} bg-white shadow-sm overflow-hidden`}>
        <div className={`px-5 py-3 ${headerBg} flex items-center gap-2`}>
          <span className={`text-sm font-semibold ${headerText}`}>Portfolio {label}</span>
        </div>
        <div className="px-5 py-6 text-center text-sm text-slate-500">
          Not started yet — click <strong>Run Now</strong> to initialise.
        </div>
      </div>
    );
  }

  const s = status;
  const returnPct = s.total_return_pct ?? 0;
  const safeTrades = Array.isArray(trades) ? trades : [];
  const openTrades = safeTrades.filter((t) => t.status === "OPEN" || t.status === "PARTIAL");
  const closedTrades = safeTrades.filter((t) => t.status === "CLOSED");
  const curveColor = returnPct >= 0 ? "#10b981" : "#ef4444";

  return (
    <div className={`rounded-xl border ${borderColor} bg-white shadow-sm overflow-hidden`}>
      {/* Header */}
      <div className={`px-5 py-3 ${headerBg} flex items-center justify-between`}>
        <span className={`text-sm font-semibold ${headerText}`}>Portfolio {label}</span>
        <span className="text-xs text-slate-500">
          {s.open_positions ?? 0}/{s.config?.max_positions ?? "?"} positions
        </span>
      </div>

      <div className="p-5 space-y-5">
        {/* Stat cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard
            label="Equity"
            value={`₹${fmt(s.current_equity, 0)}`}
            sub={`Started ₹${fmt(s.starting_capital, 0)}`}
          />
          <StatCard
            label="Return"
            value={fmtPct(returnPct)}
            sub={`P&L ₹${fmt(s.total_pnl, 0)}`}
            valueClass={colorPct(returnPct)}
          />
          <StatCard
            label="Win Rate"
            value={s.win_rate != null ? `${s.win_rate.toFixed(1)}%` : "—"}
            sub={`${s.win_count}W / ${s.loss_count}L`}
          />
          <StatCard
            label="Total Trades"
            value={String(s.total_trades)}
            sub={`${s.open_positions} open`}
          />
        </div>

        {/* Equity curve */}
        {(s.equity_curve ?? []).length > 1 ? (
          <div className="rounded-xl border bg-white p-4 shadow-sm">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-3">
              Equity Curve
            </p>
            <ResponsiveContainer width="100%" height={140}>
              <AreaChart data={s.equity_curve} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id={`grad${label}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={curveColor} stopOpacity={0.15} />
                    <stop offset="95%" stopColor={curveColor} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                <YAxis
                  tick={{ fontSize: 10 }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
                  width={52}
                />
                <Tooltip
                  formatter={(v: number | undefined) => [`₹${fmt(v ?? 0)}`, "Equity"]}
                  labelFormatter={(l) => `Date: ${l}`}
                />
                <Area
                  type="monotone"
                  dataKey="equity"
                  stroke={curveColor}
                  strokeWidth={2}
                  fill={`url(#grad${label})`}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="rounded-xl border bg-slate-50 p-4 text-center text-sm text-slate-400">
            No equity data yet — run the strategy to populate the curve.
          </div>
        )}

        {/* Trades tabs */}
        <div className="rounded-xl border bg-white shadow-sm overflow-hidden">
          <div className="flex border-b">
            {(["open", "closed"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => onTabChange(tab)}
                className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab
                    ? "border-slate-800 text-slate-800"
                    : "border-transparent text-slate-500 hover:text-slate-700"
                }`}
              >
                {tab === "open" ? `Open Positions (${openTrades.length})` : `Closed Trades (${closedTrades.length})`}
              </button>
            ))}
          </div>

          <div className="overflow-x-auto">
            {activeTab === "open" ? (
              openTrades.length === 0 ? (
                <p className="py-8 text-center text-sm text-slate-400">No open positions</p>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-slate-50 text-xs text-slate-500">
                      <th className="px-4 py-2 text-left">Symbol</th>
                      <th className="px-4 py-2 text-right">Entry</th>
                      <th className="px-4 py-2 text-right">SL</th>
                      <th className="px-4 py-2 text-right">Qty</th>
                      <th className="px-4 py-2 text-right">Value</th>
                    </tr>
                  </thead>
                  <tbody>
                    {openTrades.map((t) => (
                      <tr key={t.id} className="border-b last:border-0 hover:bg-slate-50">
                        <td className="px-4 py-2 font-medium text-slate-800">{t.symbol}</td>
                        <td className="px-4 py-2 text-right">₹{fmt(t.entry_price, 2)}</td>
                        <td className="px-4 py-2 text-right text-red-600">₹{fmt(t.sl_price, 2)}</td>
                        <td className="px-4 py-2 text-right">{t.remaining_qty}</td>
                        <td className="px-4 py-2 text-right">₹{fmt(t.position_value, 0)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )
            ) : closedTrades.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-400">No closed trades yet</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-slate-50 text-xs text-slate-500">
                    <th className="px-4 py-2 text-left">Symbol</th>
                    <th className="px-4 py-2 text-right">Entry</th>
                    <th className="px-4 py-2 text-right">P&L</th>
                    <th className="px-4 py-2 text-right">Return</th>
                    <th className="px-4 py-2 text-left">Exit</th>
                  </tr>
                </thead>
                <tbody>
                  {closedTrades.map((t) => (
                    <tr key={t.id} className="border-b last:border-0 hover:bg-slate-50">
                      <td className="px-4 py-2 font-medium text-slate-800">{t.symbol}</td>
                      <td className="px-4 py-2 text-right">₹{fmt(t.entry_price, 2)}</td>
                      <td className={`px-4 py-2 text-right font-medium ${t.gross_pnl >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                        ₹{fmt(t.gross_pnl, 0)}
                      </td>
                      <td className={`px-4 py-2 text-right ${t.pnl_pct >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                        {fmtPct(t.pnl_pct)}
                      </td>
                      <td className="px-4 py-2">
                        <ExitBadge reason={t.exit_reason} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Config */}
        {s.config && (
          <div className="rounded-xl border bg-slate-50 p-4">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">Config</p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-6 gap-y-1 text-xs text-slate-600">
              <span>Capital: ₹{fmt(s.config.capital, 0)}</span>
              <span>Stop Loss: {s.config.sl_pct}%</span>
              <span>Position Size: ₹{fmt(s.config.pos_value, 0)}</span>
              <span>Max Positions: {s.config.max_positions}</span>
              <span>EMA Fast: {s.config.ema_fast}</span>
              <span>EMA Slow: {s.config.ema_slow}</span>
              <span>Min ADT: ₹{s.config.min_adt_cr}cr</span>
              <span>Last Run: {s.last_run_date ?? "Never"}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function RsStrategyPage() {
  const [portfolios, setPortfolios] = useState<RsBothPortfolios | null>(null);
  const [trades, setTrades] = useState<RsAllTrades>({ A: [], B: [] });
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(false);
  const [running, setRunning] = useState(false);
  const [tabA, setTabA] = useState<"open" | "closed">("open");
  const [tabB, setTabB] = useState<"open" | "closed">("open");

  const fetchAll = useCallback(async () => {
    setFetchError(false);
    try {
      const [s, t] = await Promise.all([getRsStrategyStatus(), getRsStrategyTrades()]);
      setPortfolios(s);
      // Normalise: ensure both buckets are always arrays regardless of backend shape
      setTrades({
        A: Array.isArray(t?.A) ? t.A : [],
        B: Array.isArray(t?.B) ? t.B : [],
      });
    } catch {
      setFetchError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  async function handleRunNow() {
    setRunning(true);
    try {
      await runRsStrategyNow();
      toast.success("Scan started for Portfolio A & B", {
        description: "Fetching market data — results will refresh in ~45 s.",
        duration: 6000,
      });
      setTimeout(() => {
        fetchAll().finally(() => setRunning(false));
      }, 45_000);
    } catch (err: unknown) {
      toast.error("Run failed — backend unreachable", {
        description: err instanceof Error ? err.message : "Check that the server is running.",
      });
      setRunning(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">RS EMA50×200 Strategy</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Dual portfolio paper trading — ₹10,00,000 each · max 15 positions each · 10% SL
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchAll}
            disabled={loading}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-50"
          >
            Refresh
          </button>
          <button
            onClick={handleRunNow}
            disabled={running || loading}
            className="rounded-lg bg-slate-800 px-4 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
          >
            {running ? "Running…" : "Run Now"}
          </button>
        </div>
      </div>

      {/* Error / loading states */}
      {loading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {["A", "B"].map((l) => (
            <div key={l} className="rounded-xl border bg-white shadow-sm p-8 text-center text-sm text-slate-400">
              Loading Portfolio {l}…
            </div>
          ))}
        </div>
      ) : fetchError ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
          Could not reach the backend. Check that the server is running and try again.
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2">
          <PortfolioPanel
            label="A"
            status={portfolios?.A ?? null}
            trades={trades.A}
            activeTab={tabA}
            onTabChange={setTabA}
          />
          <PortfolioPanel
            label="B"
            status={portfolios?.B ?? null}
            trades={trades.B}
            activeTab={tabB}
            onTabChange={setTabB}
          />
        </div>
      )}
    </div>
  );
}
