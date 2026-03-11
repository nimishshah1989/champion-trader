"use client";

import { useEffect, useState, useCallback } from "react";
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

function SpinnerIcon() {
  return (
    <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
    </svg>
  );
}

// --- Main Page ---

export default function ActionsPage() {
  const { settings, effectiveRpt } = useSettings();

  const [alerts, setAlerts] = useState<ActionAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [actingIds, setActingIds] = useState<Set<number>>(new Set());
  const [lastChecked, setLastChecked] = useState<string | null>(null);

  // Derived data
  const buyAlerts = alerts.filter((a) => a.alert_category === "BUY" && a.status === "NEW");
  const sellAlerts = alerts.filter((a) => a.alert_category === "SELL" && a.status === "NEW");
  const criticalSellAlerts = sellAlerts.filter((a) => a.alert_type === "SL_HIT");
  const profitSellAlerts = sellAlerts.filter((a) => a.alert_type !== "SL_HIT");

  // Data fetching
  const fetchAlerts = useCallback(async () => {
    try {
      setError(null);
      const data = await getActionAlerts(undefined, "NEW");
      setAlerts(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to fetch action alerts";
      setError(message);
      toast.error("Failed to load action alerts");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  // Handlers
  async function handleRefreshPrices() {
    setRefreshing(true);
    try {
      const result = await checkPrices(settings.accountValue, effectiveRpt);
      setLastChecked(result.last_checked);
      const totalAlerts = result.buy_alerts.length + result.sell_alerts.length;
      if (totalAlerts > 0) {
        toast.success(`${totalAlerts} alert${totalAlerts !== 1 ? "s" : ""} generated (${result.prices_fetched} prices checked)`);
      } else {
        toast.info(`No new signals. ${result.prices_fetched} prices checked.`);
      }
      await fetchAlerts();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to check prices");
    } finally {
      setRefreshing(false);
    }
  }

  async function handleAct(id: number) {
    setActingIds((prev) => new Set(prev).add(id));
    try {
      await actOnAlert(id);
      const a = alerts.find((x) => x.id === id);
      toast.success(`${a?.symbol ?? "Alert"} — ${a?.alert_category === "BUY" ? "Trade taken" : "Exit executed"}`);
      await fetchAlerts();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to act on alert");
    } finally {
      setActingIds((prev) => { const n = new Set(prev); n.delete(id); return n; });
    }
  }

  async function handleDismiss(id: number) {
    setActingIds((prev) => new Set(prev).add(id));
    try {
      await dismissAlert(id);
      const a = alerts.find((x) => x.id === id);
      toast.success(`${a?.symbol ?? "Alert"} dismissed`);
      await fetchAlerts();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to dismiss alert");
    } finally {
      setActingIds((prev) => { const n = new Set(prev); n.delete(id); return n; });
    }
  }

  // Render
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-800 flex items-center gap-2">
            <span>🎯</span> Actions
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Actionable BUY and SELL signals from price checks
          </p>
        </div>
        <span className="text-xs text-slate-400 font-mono tabular-nums">
          {buyAlerts.length} buy / {sellAlerts.length} sell
        </span>
      </div>

      {/* Info Banner */}
      <InfoBanner title="Quick Reference — Action Alert Terms" storageKey="actions">
        <Term label="Trigger Break">Stock price breaks above the trigger level. Entry signal.</Term>
        <Term label="Stop Loss Hit">Price fell below stop loss. Mandatory full exit.</Term>
        <Term label="2R Target">Price reached 2x the risk (True Range %). Exit 20% of position.</Term>
        <Term label="Normal Exit">Price reached 4x True Range %. Exit another 20%.</Term>
        <Term label="Great Exit">Price reached 8x True Range %. Exit 40% of position.</Term>
        <Term label="Excellent Exit">Price reached 12x True Range %. Exit 80% of remaining.</Term>
        <Term label="Exit Framework">2R = 20% out, Normal = 20%, Great = 40%, Excellent = 80%. Remaining rides with trailing stop.</Term>
      </InfoBanner>

      {/* Controls Bar */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-3 text-xs text-slate-500">
            <span>
              Account: <span className="font-mono font-semibold text-slate-700">₹{formatLakhs(settings.accountValue)}</span>
            </span>
            <span className="text-slate-300">|</span>
            <span>
              Risk Per Trade: <span className="font-mono font-semibold text-slate-700">{effectiveRpt.toFixed(2)}%</span>
            </span>
            <span className="text-slate-300">|</span>
            <span className="text-[10px] text-slate-400">
              Change in <span className="text-teal-600 font-medium">Settings</span> (sidebar gear icon)
            </span>
          </div>
          <div className="flex-1" />
          <button
            onClick={handleRefreshPrices}
            disabled={refreshing}
            className="bg-teal-600 text-white font-medium px-5 py-2 rounded-lg hover:bg-teal-700 transition-colors text-sm disabled:opacity-50 flex items-center gap-2"
          >
            {refreshing ? (<><SpinnerIcon /> Checking...</>) : "Refresh Prices"}
          </button>
          {lastChecked && (
            <span className="text-xs text-slate-400">Last checked: {formatTime(lastChecked)}</span>
          )}
        </div>
      </div>

      {/* Error state */}
      {error && !loading && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <p className="text-sm text-red-600 font-medium mb-2">Failed to load action alerts</p>
          <p className="text-xs text-red-400 mb-3">{error}</p>
          <button
            onClick={() => { setLoading(true); fetchAlerts(); }}
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
            <p className="text-xs text-slate-400">Stocks breaking above trigger levels. Review and take trade.</p>
          )}
        </div>
        {loading && <SectionSkeleton count={3} />}
        {!loading && !error && buyAlerts.length === 0 && (
          <EmptyState icon="📡" message="No buy signals right now. Click Refresh Prices to scan for trigger breaks." />
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
            <p className="text-xs text-slate-400">Active trades hitting targets or stop losses. Execute exits.</p>
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
                <SellAlertCard key={alert.id} alert={alert} onAct={handleAct} onDismiss={handleDismiss} isActing={actingIds.has(alert.id)} />
              ))}
            </div>
          </div>
        )}

        {/* Profit-taking exits */}
        {!loading && !error && profitSellAlerts.length > 0 && (
          <div>
            {criticalSellAlerts.length > 0 && (
              <p className="text-xs text-amber-600 font-semibold uppercase tracking-wider mb-2">Profit-Taking Exits</p>
            )}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {profitSellAlerts.map((alert) => (
                <SellAlertCard key={alert.id} alert={alert} onAct={handleAct} onDismiss={handleDismiss} isActing={actingIds.has(alert.id)} />
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
