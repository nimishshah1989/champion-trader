"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getRsStrategyStatus,
  getRsStrategyTrades,
  runRsStrategyNow,
  type RsPortfolioStatus,
  type RsStrategyTrade,
  type RsRunNowResult,
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

// ---------------------------------------------------------------------------
// Stat card
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
      <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">{label}</p>
      <p className={`text-2xl font-bold ${valueClass ?? "text-slate-800"}`}>{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Equity curve
// ---------------------------------------------------------------------------

function EquityCurve({ data }: { data: { date: string; equity: number }[] }) {
  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-40 text-slate-400 text-sm">
        No equity data yet — run the strategy to populate the curve.
      </div>
    );
  }

  const start = data[0].equity;
  const end = data[data.length - 1].equity;
  const positive = end >= start;

  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
            <stop
              offset="5%"
              stopColor={positive ? "#10b981" : "#ef4444"}
              stopOpacity={0.25}
            />
            <stop
              offset="95%"
              stopColor={positive ? "#10b981" : "#ef4444"}
              stopOpacity={0.02}
            />
          </linearGradient>
        </defs>
        <XAxis
          dataKey="date"
          tick={{ fontSize: 10 }}
          tickFormatter={(v) => v.slice(5)}
          minTickGap={40}
        />
        <YAxis
          tick={{ fontSize: 10 }}
          tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
          width={52}
        />
        <Tooltip
          formatter={(v: number) => [`₹${fmt(v)}`, "Equity"]}
          labelFormatter={(l) => `Date: ${l}`}
        />
        <Area
          type="monotone"
          dataKey="equity"
          stroke={positive ? "#10b981" : "#ef4444"}
          strokeWidth={2}
          fill="url(#equityGrad)"
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// ---------------------------------------------------------------------------
// Open positions table
// ---------------------------------------------------------------------------

function OpenPositionsTable({ trades }: { trades: RsPortfolioStatus["open_trades"] }) {
  if (!trades.length) {
    return <p className="text-sm text-slate-400 py-4 text-center">No open positions</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-xs text-slate-500 uppercase tracking-wide">
            <th className="text-left py-2 pr-4">Symbol</th>
            <th className="text-right py-2 pr-4">Entry</th>
            <th className="text-right py-2 pr-4">Qty</th>
            <th className="text-right py-2 pr-4">Stop</th>
            <th className="text-right py-2 pr-4">Risk</th>
            <th className="text-right py-2">Value</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => (
            <tr key={t.symbol} className="border-b last:border-0 hover:bg-slate-50">
              <td className="py-2 pr-4 font-medium text-slate-800">{t.symbol}</td>
              <td className="py-2 pr-4 text-right">₹{fmt(t.entry_price, 2)}</td>
              <td className="py-2 pr-4 text-right">{t.qty}</td>
              <td className="py-2 pr-4 text-right text-red-600">₹{fmt(t.sl_price, 2)}</td>
              <td className="py-2 pr-4 text-right">₹{fmt(t.rpt_amount, 0)}</td>
              <td className="py-2 text-right">₹{fmt(t.position_value, 0)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Closed trades table
// ---------------------------------------------------------------------------

function ClosedTradesTable({ trades }: { trades: RsStrategyTrade[] }) {
  const closed = trades.filter((t) => t.status === "CLOSED");
  if (!closed.length) {
    return <p className="text-sm text-slate-400 py-4 text-center">No closed trades yet</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-xs text-slate-500 uppercase tracking-wide">
            <th className="text-left py-2 pr-4">Symbol</th>
            <th className="text-right py-2 pr-4">Entry</th>
            <th className="text-right py-2 pr-4">Exit</th>
            <th className="text-right py-2 pr-4">P&L</th>
            <th className="text-right py-2 pr-4">P&L %</th>
            <th className="text-right py-2 pr-4">R</th>
            <th className="text-left py-2">Reason</th>
          </tr>
        </thead>
        <tbody>
          {closed
            .sort((a, b) => (b.exit_date ?? "").localeCompare(a.exit_date ?? ""))
            .map((t) => (
              <tr key={t.id} className="border-b last:border-0 hover:bg-slate-50">
                <td className="py-2 pr-4 font-medium text-slate-800">{t.symbol}</td>
                <td className="py-2 pr-4 text-right text-xs">
                  <div>{t.entry_date?.slice(0, 10) ?? "—"}</div>
                  <div className="text-slate-500">₹{fmt(t.entry_price, 2)}</div>
                </td>
                <td className="py-2 pr-4 text-right text-xs">
                  <div>{t.exit_date?.slice(0, 10) ?? "—"}</div>
                </td>
                <td className={`py-2 pr-4 text-right font-medium ${colorPct(t.gross_pnl)}`}>
                  ₹{fmt(t.gross_pnl, 0)}
                </td>
                <td className={`py-2 pr-4 text-right ${colorPct(t.pnl_pct)}`}>
                  {fmtPct(t.pnl_pct)}
                </td>
                <td className={`py-2 pr-4 text-right ${colorPct(t.r_multiple)}`}>
                  {t.r_multiple != null ? t.r_multiple.toFixed(2) : "—"}
                </td>
                <td className="py-2 text-xs">
                  <span
                    className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                      t.exit_reason === "STOP_LOSS"
                        ? "bg-red-50 text-red-700"
                        : "bg-blue-50 text-blue-700"
                    }`}
                  >
                    {t.exit_reason ?? "—"}
                  </span>
                </td>
              </tr>
            ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Run-Now result toast content
// ---------------------------------------------------------------------------

function showRunResult(result: RsRunNowResult) {
  const r = result.result;
  const lines = [
    `Date: ${r.date}`,
    r.entries.length ? `Entries: ${r.entries.join(", ")}` : "No new entries",
    r.exits.length ? `Exits: ${r.exits.join(", ")}` : "No exits",
    `Open positions: ${r.open_positions} | Equity: ₹${fmt(r.equity, 0)}`,
  ];
  if (r.errors.length) lines.push(`Errors: ${r.errors.join("; ")}`);
  toast.success(result.message, { description: lines.join("\n"), duration: 8000 });
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function RsStrategyPage() {
  const [status, setStatus] = useState<RsPortfolioStatus | null>(null);
  const [trades, setTrades] = useState<RsStrategyTrade[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [activeTab, setActiveTab] = useState<"open" | "closed">("open");

  const fetchAll = useCallback(async () => {
    try {
      const [s, t] = await Promise.allSettled([getRsStrategyStatus(), getRsStrategyTrades()]);
      if (s.status === "fulfilled") setStatus(s.value);
      if (t.status === "fulfilled") setTrades(t.value);
    } catch {
      // silently swallow
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
      const result = await runRsStrategyNow();
      showRunResult(result);
      await fetchAll();
    } catch (err: unknown) {
      toast.error("Run failed", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
    } finally {
      setRunning(false);
    }
  }

  const returnPct = status?.total_return_pct ?? 0;
  const winRate = status?.win_rate;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">RS EMA50×200 Strategy</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Automated paper trading — RS golden/death cross signals on NSE
          </p>
        </div>
        <button
          onClick={handleRunNow}
          disabled={running || loading}
          className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {running ? "Running…" : "Run Now"}
        </button>
      </div>

      {/* Summary cards */}
      {loading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 animate-pulse">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 rounded-xl border bg-slate-100" />
          ))}
        </div>
      ) : status?.error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
          {status.error}
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            label="Current Equity"
            value={`₹${fmt(status?.current_equity ?? 100000, 0)}`}
            sub={`Started ₹${fmt(status?.starting_capital ?? 100000, 0)}`}
            valueClass={colorPct(returnPct)}
          />
          <StatCard
            label="Total Return"
            value={fmtPct(returnPct)}
            sub={`P&L ₹${fmt(status?.total_pnl ?? 0, 0)}`}
            valueClass={colorPct(returnPct)}
          />
          <StatCard
            label="Open Positions"
            value={String(status?.open_positions ?? 0)}
            sub={`of ${status?.config?.max_positions ?? 15} max`}
          />
          <StatCard
            label="Win Rate"
            value={winRate != null ? `${winRate.toFixed(1)}%` : "—"}
            sub={`${status?.win_count ?? 0}W / ${status?.loss_count ?? 0}L of ${status?.total_trades ?? 0} trades`}
          />
        </div>
      )}

      {/* Equity curve */}
      <div className="rounded-xl border bg-white px-5 py-4 shadow-sm">
        <h2 className="text-sm font-medium text-slate-700 mb-3">Equity Curve</h2>
        {loading ? (
          <div className="h-[200px] animate-pulse bg-slate-100 rounded" />
        ) : (
          <EquityCurve data={status?.equity_curve ?? []} />
        )}
      </div>

      {/* Positions & Trades */}
      <div className="rounded-xl border bg-white shadow-sm">
        {/* Tabs */}
        <div className="border-b px-5">
          <div className="flex gap-6">
            {(["open", "closed"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab
                    ? "border-slate-800 text-slate-800"
                    : "border-transparent text-slate-500 hover:text-slate-700"
                }`}
              >
                {tab === "open"
                  ? `Open Positions (${status?.open_positions ?? 0})`
                  : `Closed Trades (${trades.filter((t) => t.status === "CLOSED").length})`}
              </button>
            ))}
          </div>
        </div>

        <div className="px-5 py-4">
          {loading ? (
            <div className="h-24 animate-pulse bg-slate-100 rounded" />
          ) : activeTab === "open" ? (
            <OpenPositionsTable trades={status?.open_trades ?? []} />
          ) : (
            <ClosedTradesTable trades={trades} />
          )}
        </div>
      </div>

      {/* Strategy Config */}
      {status?.config && (
        <div className="rounded-xl border bg-white px-5 py-4 shadow-sm">
          <h2 className="text-sm font-medium text-slate-700 mb-3">Strategy Config</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-2 text-sm">
            <div>
              <span className="text-slate-500">Capital</span>
              <span className="ml-2 font-medium">₹{fmt(status.config.capital, 0)}</span>
            </div>
            <div>
              <span className="text-slate-500">RPT</span>
              <span className="ml-2 font-medium">{status.config.rpt_pct}%</span>
            </div>
            <div>
              <span className="text-slate-500">Stop Loss</span>
              <span className="ml-2 font-medium">{status.config.sl_pct}%</span>
            </div>
            <div>
              <span className="text-slate-500">Max Positions</span>
              <span className="ml-2 font-medium">{status.config.max_positions}</span>
            </div>
            <div>
              <span className="text-slate-500">EMA Fast</span>
              <span className="ml-2 font-medium">{status.config.ema_fast}</span>
            </div>
            <div>
              <span className="text-slate-500">EMA Slow</span>
              <span className="ml-2 font-medium">{status.config.ema_slow}</span>
            </div>
            <div>
              <span className="text-slate-500">Min ADT</span>
              <span className="ml-2 font-medium">₹{status.config.min_adt_cr}Cr</span>
            </div>
            <div>
              <span className="text-slate-500">Position Size</span>
              <span className="ml-2 font-medium">₹{fmt(status.config.pos_value, 0)}</span>
            </div>
          </div>
          {status.last_run_date && (
            <p className="mt-3 text-xs text-slate-400">
              Last run: {status.last_run_date} · Next: weekdays 16:30 IST
            </p>
          )}
        </div>
      )}
    </div>
  );
}
