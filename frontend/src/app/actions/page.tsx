"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import {
  getActionAlerts,
  checkPrices,
  actOnAlert,
  dismissAlert,
  type ActionAlert,
} from "@/lib/api";
import { useSettings } from "@/contexts/settings-context";
import { toast } from "sonner";
import { InfoBanner, Term } from "@/components/info-banner";
import { BuyAlertCard } from "./components/buy-alert-card";
import { SellAlertCard } from "./components/sell-alert-card";
import { SectionSkeleton, EmptyState } from "./components/skeletons";
import { LearnSection } from "./components/learn-section";
import { formatLakhs } from "@/lib/format";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const AUTO_POLL_INTERVAL_MS = 10_000; // 10 s — just refreshes alert list from DB

function formatTime(isoStr: string): string {
  try {
    return new Date(isoStr).toLocaleString("en-IN", {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });
  } catch {
    return isoStr;
  }
}

/** Current IST time as { hour, minute } */
function getISTTime(): { hour: number; minute: number } {
  const now = new Date();
  // IST = UTC + 5:30
  const istMs = now.getTime() + (5 * 60 + 30) * 60 * 1000;
  const ist = new Date(istMs);
  return { hour: ist.getUTCHours(), minute: ist.getUTCMinutes() };
}

type MonitorStatus =
  | { state: "entry_window"; label: string; color: string }
  | { state: "market_open"; label: string; color: string }
  | { state: "market_closed"; label: string; color: string };

function getMonitorStatus(): MonitorStatus {
  const { hour, minute } = getISTTime();
  const totalMin = hour * 60 + minute;

  const marketOpen = 9 * 60 + 15;   // 09:15 IST
  const entryStart = 15 * 60;        // 15:00 IST
  const entryEnd = 15 * 60 + 30;     // 15:30 IST
  const marketClose = 15 * 60 + 30;  // 15:30 IST

  if (totalMin >= entryStart && totalMin <= entryEnd) {
    return {
      state: "entry_window",
      label: "Entry Window Active — checking every 1 min",
      color: "text-emerald-700 bg-emerald-50 border-emerald-200",
    };
  }
  if (totalMin >= marketOpen && totalMin < marketClose) {
    return {
      state: "market_open",
      label: "Exit Watch Active — checking every 2 min",
      color: "text-teal-700 bg-teal-50 border-teal-200",
    };
  }
  return {
    state: "market_closed",
    label: "Market closed — live monitoring paused",
    color: "text-slate-500 bg-slate-50 border-slate-200",
  };
}

function SpinnerIcon() {
  return (
    <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Live Monitor Badge
// ---------------------------------------------------------------------------

function LiveMonitorBadge() {
  // Defer initial status to useEffect to avoid SSR/client hydration mismatch
  // (getMonitorStatus uses new Date() which differs between server and client)
  const [status, setStatus] = useState<MonitorStatus>({
    state: "market_closed",
    label: "Loading...",
    color: "text-slate-500 bg-slate-50 border-slate-200",
  });

  // Set real status on mount + re-evaluate every 30 s
  useEffect(() => {
    setStatus(getMonitorStatus());
    const id = setInterval(() => setStatus(getMonitorStatus()), 30_000);
    return () => clearInterval(id);
  }, []);

  const pulse =
    status.state !== "market_closed"
      ? "before:animate-ping before:absolute before:inline-flex before:h-2 before:w-2 before:rounded-full before:opacity-75"
      : "";

  return (
    <span
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-medium ${status.color}`}
    >
      <span className={`relative inline-flex h-2 w-2 ${pulse}`}>
        <span
          className={`relative inline-flex h-2 w-2 rounded-full ${
            status.state === "entry_window"
              ? "bg-emerald-500"
              : status.state === "market_open"
              ? "bg-teal-500"
              : "bg-slate-400"
          }`}
        />
      </span>
      {status.label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function ActionsPage() {
  const { settings, effectiveRpt } = useSettings();

  const [alerts, setAlerts] = useState<ActionAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [manualRefreshing, setManualRefreshing] = useState(false);
  const [actingIds, setActingIds] = useState<Set<number>>(new Set());
  const [lastChecked, setLastChecked] = useState<string | null>(null);
  const [alertCount, setAlertCount] = useState<number>(0);

  // Derived data
  const buyAlerts = alerts.filter((a) => a.alert_category === "BUY" && a.status === "NEW");
  const sellAlerts = alerts.filter((a) => a.alert_category === "SELL" && a.status === "NEW");
  const criticalSellAlerts = sellAlerts.filter((a) => a.alert_type === "SL_HIT");
  const profitSellAlerts = sellAlerts.filter((a) => a.alert_type !== "SL_HIT");

  // ---------------------------------------------------------------------------
  // Auto-poll: just fetches alert list every 10 s.
  // The backend scheduler generates alerts automatically — we only need to
  // check the DB for new ones that appeared since the last render.
  // ---------------------------------------------------------------------------

  const fetchAlerts = useCallback(async (silent = false) => {
    try {
      if (!silent) setError(null);
      const data = await getActionAlerts(undefined, "NEW");

      // Notify user if new alerts appeared since last poll
      if (silent && data.length > alertCount) {
        const diff = data.length - alertCount;
        toast.info(`${diff} new alert${diff > 1 ? "s" : ""} detected`, { duration: 4000 });
      }

      setAlerts(data);
      setAlertCount(data.length);
      setLastChecked(new Date().toISOString());
    } catch (err) {
      if (!silent) {
        const message = err instanceof Error ? err.message : "Failed to fetch action alerts";
        setError(message);
        toast.error("Failed to load action alerts");
      }
    } finally {
      if (!silent) setLoading(false);
    }
  }, [alertCount]);

  // Initial load
  useEffect(() => {
    fetchAlerts(false);
    setLoading(false);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-poll every 10 s
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => {
    pollRef.current = setInterval(() => fetchAlerts(true), AUTO_POLL_INTERVAL_MS);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [fetchAlerts]);

  // ---------------------------------------------------------------------------
  // Manual "Check Now" — triggers an immediate price check on the backend,
  // then refreshes the alert list. Use this outside market hours for testing.
  // ---------------------------------------------------------------------------

  async function handleManualCheck() {
    setManualRefreshing(true);
    try {
      const result = await checkPrices(settings.accountValue, effectiveRpt);
      setLastChecked(result.last_checked);
      const total = result.buy_alerts.length + result.sell_alerts.length;
      if (total > 0) {
        toast.success(`${total} alert${total !== 1 ? "s" : ""} found (${result.prices_fetched} prices checked)`);
      } else {
        toast.info(`No new signals. ${result.prices_fetched} prices checked.`);
      }
      await fetchAlerts(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to check prices");
    } finally {
      setManualRefreshing(false);
    }
  }

  // ---------------------------------------------------------------------------
  // Act / Dismiss
  // ---------------------------------------------------------------------------

  async function handleAct(id: number) {
    setActingIds((prev) => new Set(prev).add(id));
    try {
      await actOnAlert(id);
      const a = alerts.find((x) => x.id === id);
      toast.success(`${a?.symbol ?? "Alert"} — ${a?.alert_category === "BUY" ? "Trade taken" : "Exit executed"}`);
      await fetchAlerts(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to act on alert");
    } finally {
      setActingIds((prev) => {
        const n = new Set(prev);
        n.delete(id);
        return n;
      });
    }
  }

  async function handleDismiss(id: number) {
    setActingIds((prev) => new Set(prev).add(id));
    try {
      await dismissAlert(id);
      const a = alerts.find((x) => x.id === id);
      toast.success(`${a?.symbol ?? "Alert"} dismissed`);
      await fetchAlerts(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to dismiss alert");
    } finally {
      setActingIds((prev) => {
        const n = new Set(prev);
        n.delete(id);
        return n;
      });
    }
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-xl font-semibold text-slate-800 flex items-center gap-2">
            <span>🎯</span> Actions
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            BUY and SELL signals — generated automatically by the live monitor
          </p>
        </div>
        <LiveMonitorBadge />
      </div>

      {/* Info Banner */}
      <InfoBanner title="Quick Reference — Action Alert Terms" storageKey="actions">
        <Term label="Trigger Break">Stock price breaks above the trigger level. Entry signal.</Term>
        <Term label="Stop Loss Hit">Price fell below stop loss. Mandatory full exit.</Term>
        <Term label="2R Target">Price reached 2× the risk (True Range %). Exit 20% of position.</Term>
        <Term label="Normal Exit">Price reached 4× True Range %. Exit another 20%.</Term>
        <Term label="Great Exit">Price reached 8× True Range %. Exit 40% of position.</Term>
        <Term label="Excellent Exit">Price reached 12× True Range %. Exit 80% of remaining.</Term>
        <Term label="Exit Framework">2R=20% out, Normal=20%, Great=40%, Excellent=80%. Remaining rides with trailing stop.</Term>
      </InfoBanner>

      {/* Controls Bar */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-3 text-xs text-slate-500">
            <span>
              Account:{" "}
              <span className="font-mono font-semibold text-slate-700">
                ₹{formatLakhs(settings.accountValue)}
              </span>
            </span>
            <span className="text-slate-300">|</span>
            <span>
              RPT:{" "}
              <span className="font-mono font-semibold text-slate-700">{effectiveRpt.toFixed(2)}%</span>
            </span>
            <span className="text-slate-300">|</span>
            <span className="text-[10px] text-slate-400">
              Change in <span className="text-teal-600 font-medium">Settings</span> (sidebar gear)
            </span>
          </div>

          <div className="flex-1" />

          {/* Alert count + last checked */}
          <div className="flex items-center gap-3">
            {lastChecked && (
              <span className="text-[11px] text-slate-400 tabular-nums">
                Updated {formatTime(lastChecked)}
              </span>
            )}
            <span className="text-[11px] font-mono text-slate-500 bg-slate-50 border border-slate-200 rounded px-2 py-1">
              {buyAlerts.length} buy · {sellAlerts.length} sell
            </span>
          </div>

          {/* Manual override — useful for testing outside market hours */}
          <button
            onClick={handleManualCheck}
            disabled={manualRefreshing}
            className="text-xs font-medium px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 transition-colors disabled:opacity-50 flex items-center gap-1.5"
          >
            {manualRefreshing ? (
              <>
                <SpinnerIcon />
                Checking…
              </>
            ) : (
              "Check Now"
            )}
          </button>
        </div>
      </div>

      {/* Error state */}
      {error && !loading && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <p className="text-sm text-red-600 font-medium mb-2">Failed to load action alerts</p>
          <p className="text-xs text-red-400 mb-3">{error}</p>
          <button
            onClick={() => {
              setLoading(true);
              fetchAlerts(false);
            }}
            className="bg-red-600 text-white text-xs font-medium px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* BUY SIGNALS */}
      <div>
        <div className="flex items-center gap-3 mb-4">
          <div className="bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-2.5 flex items-center gap-2">
            <span className="text-sm font-bold text-emerald-700">BUY SIGNALS</span>
            <span className="text-xs text-slate-400 font-mono">({buyAlerts.length})</span>
          </div>
          {!loading && buyAlerts.length > 0 && (
            <p className="text-xs text-slate-400">
              Stocks breaking above trigger levels — review and take the trade.
            </p>
          )}
        </div>
        {loading && <SectionSkeleton count={3} />}
        {!loading && !error && buyAlerts.length === 0 && (
          <EmptyState
            icon="📡"
            message="No buy signals yet. The system checks automatically at 3 PM — 3:30 PM. You can also click Check Now."
          />
        )}
        {!loading && !error && buyAlerts.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {buyAlerts.map((alert) => (
              <BuyAlertCard
                key={alert.id}
                alert={alert}
                onAct={handleAct}
                onDismiss={handleDismiss}
                isActing={actingIds.has(alert.id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* SELL SIGNALS */}
      <div>
        <div className="flex items-center gap-3 mb-4">
          <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-2.5 flex items-center gap-2">
            <span className="text-sm font-bold text-red-700">SELL SIGNALS</span>
            <span className="text-xs text-slate-400 font-mono">({sellAlerts.length})</span>
          </div>
          {!loading && sellAlerts.length > 0 && (
            <p className="text-xs text-slate-400">
              Active trades hitting targets or stop losses — execute exits.
            </p>
          )}
        </div>
        {loading && <SectionSkeleton count={2} />}
        {!loading && !error && sellAlerts.length === 0 && (
          <EmptyState icon="🛡" message="No sell signals. All positions within normal range." />
        )}

        {/* Critical SL hits first */}
        {!loading && !error && criticalSellAlerts.length > 0 && (
          <div className="mb-4">
            <p className="text-xs text-red-500 font-semibold uppercase tracking-wider mb-2">
              Stop Loss Hits — Immediate Action Required
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {criticalSellAlerts.map((alert) => (
                <SellAlertCard
                  key={alert.id}
                  alert={alert}
                  onAct={handleAct}
                  onDismiss={handleDismiss}
                  isActing={actingIds.has(alert.id)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Profit-taking exits */}
        {!loading && !error && profitSellAlerts.length > 0 && (
          <div>
            {criticalSellAlerts.length > 0 && (
              <p className="text-xs text-amber-600 font-semibold uppercase tracking-wider mb-2">
                Profit-Taking Exits
              </p>
            )}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {profitSellAlerts.map((alert) => (
                <SellAlertCard
                  key={alert.id}
                  alert={alert}
                  onAct={handleAct}
                  onDismiss={handleDismiss}
                  isActing={actingIds.has(alert.id)}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Learn Section */}
      <LearnSection />
    </div>
  );
}
