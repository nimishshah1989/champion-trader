"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getRsStrategyStatus,
  getRsStrategyTrades,
  runRsStrategyNow,
  type RsPortfolioStatus,
  type RsStrategyTrade,
  type RsStrategyStatusResponse,
  type RsStrategyTradesResponse,
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

function fmt(n: number | null | undefined, decimals = 0): string {
  if (n == null) return "—";
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

function StatCard({ label, value, sub, valueClass }: {
  label: string; value: string; sub?: string; valueClass?: string;
}) {
  return (
    <div className="rounded-xl border bg-white px-5 py-4 shadow-sm">
      <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">{label}</p>
      <p className={`text-2xl font-bold ${valueClass ?? "text-slate-800"}`}>{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
    </div>
  );
}

function EquityCurve({ data }: { data: { date: string; equity: number }[] }) {
  if (!data || data.length === 0) {
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
            <stop offset="5%" stopColor={positive ? "#10b981" : "#ef4444"} stopOpacity={0.25} />
            <stop offset="95%" stopColor={positive ? "#10b981" : "#ef4444"} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={(v) => v.slice(5)} minTickGap={40} />
        <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} width={52} />
        <Tooltip
          formatter={(v: number | undefined) => [`₹${fmt(v ?? 0)}`, "Equity"]}
          labelFormatter={(l) => `Date: ${l}`}
        />
        <Area type="monotone" dataKey="equity" stroke={positive ? "#10b981" : "#ef4444"} strokeWidth={2} fill="url(#equityGrad)" dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function OpenPositionsTable({ trades }: { trades: RsPortfolioStatus["open_trades"] }) {
  const safe = Array.isArray(trades) ? trades : [];
  if (!safe.length) {
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
          {safe.map((t) => (
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

function ClosedTradesTable({ trades }: { trades: RsStrategyTrade[] }) {
  const safe = Array.isArray(trades) ? trades : [];
  const closed = safe.filter((t) => t.status === "CLOSED");
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
                <td className={`py-2 pr-4 text-right ${colorPct(t.pnl_pct)}`}>{fmtPct(t.pnl_pct)}</td>
                <td className={`py-2 pr-4 text-right ${colorPct(t.r_multiple)}`}>
                  {t.r_multiple != null ? t.r_multiple.toFixed(2) : "—"}
                </td>
                <td className="py-2 text-xs">
                  <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                    t.exit_reason === "STOP_LOSS" ? "bg-red-50 text-red-700" : "bg-blue-50 text-blue-700"
                  }`}>
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

function PortfolioPanel({
  portfolio,
  trades,
  label,
}: {
  portfolio: RsPortfolioStatus;
  trades: RsStrategyTrade[];
  label: string;
}) {
  const [activeTab, setActiveTab] = useState<"open" | "closed">("open");
  const returnPct = portfolio.total_return_pct ?? 0;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Current Equity"
          value={`₹${fmt(portfolio.current_equity, 0)}`}
          sub={`Started ₹${fmt(portfolio.starting_capital, 0)}`}
          valueClass={colorPct(returnPct)}
        />
        <StatCard
          label="Total Return"
          value={fmtPct(returnPct)}
          sub={`P&L ₹${fmt(portfolio.total_pnl, 0)}`}
          valueClass={colorPct(returnPct)}
        />
        <StatCard
          label="Open Positions"
          value={String(portfolio.open_positions ?? 0)}
          sub={`of ${portfolio.config?.max_positions ?? 15} max`}
        />
        <StatCard
          label="Win Rate"
          value={portfolio.win_rate != null ? `${portfolio.win_rate.toFixed(1)}%` : "—"}
          sub={`${portfolio.win_count ?? 0}W / ${portfolio.loss_count ?? 0}L of ${portfolio.total_trades ?? 0} trades`}
        />
      </div>

      <div className="rounded-xl border bg-white px-5 py-4 shadow-sm">
        <h3 className="text-sm font-medium text-slate-700 mb-3">Equity Curve — {label}</h3>
        <EquityCurve data={portfolio.equity_curve ?? []} />
      </div>

      <div className="rounded-xl border bg-white shadow-sm">
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
                  ? `Open Positions (${portfolio.open_positions ?? 0})`
                  : `Closed Trades (${Array.isArray(trades) ? trades.filter((t) => t.status === "CLOSED").length : 0})`}
              </button>
            ))}
          </div>
        </div>
        <div className="px-5 py-4">
          {activeTab === "open" ? (
            <OpenPositionsTable trades={portfolio.open_trades ?? []} />
          ) : (
            <ClosedTradesTable trades={trades} />
          )}
        </div>
      </div>

      {portfolio.config && (
        <div className="rounded-xl border bg-white px-5 py-4 shadow-sm">
          <h3 className="text-sm font-medium text-slate-700 mb-3">Config — {label}</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-2 text-sm">
            {[
              ["Capital", `₹${fmt(portfolio.config.capital, 0)}`],
              ["RPT", `${portfolio.config.rpt_pct}%`],
              ["Stop Loss", `${portfolio.config.sl_pct}%`],
              ["Max Positions", `${portfolio.config.max_positions}`],
              ["EMA Fast", `${portfolio.config.ema_fast}`],
              ["EMA Slow", `${portfolio.config.ema_slow}`],
              ["Min ADT", `₹${portfolio.config.min_adt_cr}Cr`],
              ["Position Size", `₹${fmt(portfolio.config.pos_value, 0)}`],
            ].map(([k, v]) => (
              <div key={k}>
                <span className="text-slate-500">{k}</span>
                <span className="ml-2 font-medium">{v}</span>
              </div>
            ))}
          </div>
          {portfolio.last_run_date && (
            <p className="mt-3 text-xs text-slate-400">
              Last run: {portfolio.last_run_date} · Next: weekdays 16:30 IST
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default function RsStrategyPage() {
  const [statusData, setStatusData] = useState<RsStrategyStatusResponse | null>(null);
  const [tradesData, setTradesData] = useState<RsStrategyTradesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(false);
  const [running, setRunning] = useState(false);
  const [activePortfolio, setActivePortfolio] = useState<"A" | "B">("A");

  const fetchAll = useCallback(async () => {
    setFetchError(false);
    try {
      const [s, t] = await Promise.allSettled([getRsStrategyStatus(), getRsStrategyTrades()]);
      if (s.status === "fulfilled" && s.value && typeof s.value === "object") {
        setStatusData(s.value as RsStrategyStatusResponse);
      } else {
        setFetchError(true);
      }
      if (t.status === "fulfilled" && t.value && typeof t.value === "object") {
        setTradesData(t.value as RsStrategyTradesResponse);
      }
    } catch {
      setFetchError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  async function handleRunNow() {
    setRunning(true);
    try {
      await runRsStrategyNow();
      toast.success("Scan started", {
        description: "Fetching market data & computing signals — results will refresh in ~45 s.",
        duration: 6000,
      });
      setTimeout(() => { fetchAll().finally(() => setRunning(false)); }, 45_000);
    } catch (err: unknown) {
      toast.error("Run failed — backend unreachable", {
        description: err instanceof Error ? err.message : "Check that the server is running.",
      });
      setRunning(false);
    }
  }

  const portfolio = statusData?.[activePortfolio];
  const trades = tradesData?.[activePortfolio] ?? [];

  return (
    <div className="space-y-6">
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

      {/* Portfolio switcher */}
      <div className="flex gap-2">
        {(["A", "B"] as const).map((p) => (
          <button
            key={p}
            onClick={() => setActivePortfolio(p)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              activePortfolio === p
                ? "bg-slate-800 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            Portfolio {p}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 animate-pulse">
          {[...Array(4)].map((_, i) => <div key={i} className="h-24 rounded-xl border bg-slate-100" />)}
        </div>
      ) : fetchError ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
          Could not reach the backend. Check that the server is running and try again.
        </div>
      ) : !portfolio ? (
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-5 py-4 text-sm text-slate-500">
          Portfolio {activePortfolio} not started yet. Click <strong>Run Now</strong> to run the first scan.
        </div>
      ) : (
        <PortfolioPanel
          portfolio={portfolio}
          trades={Array.isArray(trades) ? trades : []}
          label={`Portfolio ${activePortfolio}`}
        />
      )}
    </div>
  );
}
