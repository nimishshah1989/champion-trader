"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getActionAlerts,
  checkPrices,
  actOnAlert,
  dismissAlert,
  getLatestStance,
  type ActionAlert,
} from "@/lib/api";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import { InfoBanner, Term } from "@/components/info-banner";

// ---------------------------------------------------------------------------
// Types & Constants
// ---------------------------------------------------------------------------

interface ParsedTargets {
  target_2r?: number;
  target_ne?: number;
  target_ge?: number;
  target_ee?: number;
  [key: string]: unknown;
}

const DEFAULT_ACCOUNT_VALUE = 500000;
const DEFAULT_RPT_PCT = 0.5;

const formatINR = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 2,
});

const formatINRCompact = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

/** Alert type labels for display */
const ALERT_TYPE_LABELS: Record<string, string> = {
  TRIGGER_BREAK: "Trigger Break",
  SL_HIT: "Stop Loss Hit",
  "2R_HIT": "2R Target Hit",
  NE_HIT: "Normal Exit Hit",
  GE_HIT: "Great Exit Hit",
  EE_HIT: "Excellent Exit Hit",
  FINAL_EXIT: "Final Exit",
};

/** Colors and styling for sell alert types */
const SELL_ALERT_STYLE: Record<string, { border: string; badge: string; badgeText: string }> = {
  SL_HIT: {
    border: "border-l-red-500",
    badge: "bg-red-600 text-white",
    badgeText: "STOP LOSS",
  },
  "2R_HIT": {
    border: "border-l-amber-500",
    badge: "bg-amber-500 text-white",
    badgeText: "2R TARGET",
  },
  NE_HIT: {
    border: "border-l-amber-500",
    badge: "bg-amber-500 text-white",
    badgeText: "NORMAL EXIT",
  },
  GE_HIT: {
    border: "border-l-teal-500",
    badge: "bg-teal-600 text-white",
    badgeText: "GREAT EXIT",
  },
  EE_HIT: {
    border: "border-l-emerald-500",
    badge: "bg-emerald-600 text-white",
    badgeText: "EXCELLENT EXIT",
  },
  FINAL_EXIT: {
    border: "border-l-slate-500",
    badge: "bg-slate-600 text-white",
    badgeText: "FINAL EXIT",
  },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function parseTargets(dataStr: string | null): ParsedTargets | null {
  if (!dataStr) return null;
  try {
    return JSON.parse(dataStr) as ParsedTargets;
  } catch {
    return null;
  }
}

function formatTime(isoStr: string): string {
  try {
    const date = new Date(isoStr);
    return date.toLocaleString("en-IN", {
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

// ---------------------------------------------------------------------------
// Skeleton Loaders
// ---------------------------------------------------------------------------

function AlertCardSkeleton() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
      <div className="flex items-center gap-3">
        <Skeleton className="h-6 w-20 bg-slate-100 rounded" />
        <Skeleton className="h-5 w-28 bg-slate-100" />
      </div>
      <div className="grid grid-cols-3 gap-4">
        <Skeleton className="h-10 bg-slate-100 rounded" />
        <Skeleton className="h-10 bg-slate-100 rounded" />
        <Skeleton className="h-10 bg-slate-100 rounded" />
      </div>
      <div className="grid grid-cols-4 gap-2">
        <Skeleton className="h-8 bg-slate-100 rounded" />
        <Skeleton className="h-8 bg-slate-100 rounded" />
        <Skeleton className="h-8 bg-slate-100 rounded" />
        <Skeleton className="h-8 bg-slate-100 rounded" />
      </div>
      <div className="flex gap-2 pt-2">
        <Skeleton className="h-8 w-24 bg-slate-100 rounded" />
        <Skeleton className="h-8 w-20 bg-slate-100 rounded" />
      </div>
    </div>
  );
}

function SectionSkeleton({ count }: { count: number }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <AlertCardSkeleton key={i} />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Buy Signal Card
// ---------------------------------------------------------------------------

function BuyAlertCard({
  alert,
  onAct,
  onDismiss,
  isActing,
}: {
  alert: ActionAlert;
  onAct: (id: number) => void;
  onDismiss: (id: number) => void;
  isActing: boolean;
}) {
  const targets = parseTargets(alert.data);

  return (
    <div className="bg-white rounded-xl border border-slate-200 border-l-4 border-l-emerald-500 p-5 hover:border-slate-300 transition-colors">
      {/* Header: Symbol + Badge */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-base font-bold text-slate-800 tracking-wide">
            {alert.symbol}
          </span>
          <span className="bg-emerald-600 text-white rounded px-2 py-0.5 text-xs font-bold uppercase">
            BUY
          </span>
        </div>
        <span className="text-[10px] text-slate-400 uppercase tracking-wider font-medium">
          {ALERT_TYPE_LABELS[alert.alert_type] || alert.alert_type}
        </span>
      </div>

      {/* Price Metrics */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs mb-3">
        {alert.trigger_price !== null && (
          <div>
            <span className="text-slate-400">Trigger</span>
            <span className="ml-1.5 font-mono font-semibold text-slate-700">
              {formatINR.format(alert.trigger_price)}
            </span>
          </div>
        )}
        {alert.current_price !== null && (
          <div>
            <span className="text-slate-400">CMP</span>
            <span className="ml-1.5 font-mono font-semibold text-emerald-600">
              {formatINR.format(alert.current_price)}
            </span>
          </div>
        )}
        {alert.suggested_entry_price !== null && (
          <div>
            <span className="text-slate-400">Entry</span>
            <span className="ml-1.5 font-mono font-semibold text-slate-700">
              {formatINR.format(alert.suggested_entry_price)}
            </span>
          </div>
        )}
        {alert.suggested_sl_price !== null && (
          <div>
            <span className="text-slate-400">SL</span>
            <span className="ml-1.5 font-mono font-semibold text-red-600">
              {formatINR.format(alert.suggested_sl_price)}
            </span>
          </div>
        )}
      </div>

      {/* Quantity row */}
      <div className="grid grid-cols-3 gap-x-4 text-xs mb-3">
        {alert.suggested_qty !== null && (
          <div>
            <span className="text-slate-400">Qty</span>
            <span className="ml-1.5 font-mono font-semibold text-slate-700">
              {alert.suggested_qty}
            </span>
          </div>
        )}
        {alert.suggested_half_qty !== null && (
          <div>
            <span className="text-slate-400">Half Qty</span>
            <span className="ml-1.5 font-mono font-semibold text-slate-700">
              {alert.suggested_half_qty}
            </span>
          </div>
        )}
        {alert.trp_pct !== null && (
          <div>
            <span className="text-slate-400">TRP%</span>
            <span className="ml-1.5 font-mono font-semibold text-slate-700">
              {alert.trp_pct.toFixed(2)}%
            </span>
          </div>
        )}
      </div>

      {/* Targets row from parsed data */}
      {targets && (targets.target_2r || targets.target_ne || targets.target_ge || targets.target_ee) && (
        <div className="bg-slate-50 rounded-lg px-3 py-2 mb-3">
          <p className="text-[10px] text-slate-400 uppercase tracking-wider font-medium mb-1.5">
            Exit Targets
          </p>
          <div className="grid grid-cols-4 gap-2 text-xs">
            {targets.target_2r != null && (
              <div className="text-center">
                <span className="block text-[10px] text-slate-400">2R</span>
                <span className="font-mono font-semibold text-slate-700">
                  {formatINRCompact.format(targets.target_2r as number)}
                </span>
              </div>
            )}
            {targets.target_ne != null && (
              <div className="text-center">
                <span className="block text-[10px] text-slate-400">NE</span>
                <span className="font-mono font-semibold text-slate-700">
                  {formatINRCompact.format(targets.target_ne as number)}
                </span>
              </div>
            )}
            {targets.target_ge != null && (
              <div className="text-center">
                <span className="block text-[10px] text-slate-400">GE</span>
                <span className="font-mono font-semibold text-teal-600">
                  {formatINRCompact.format(targets.target_ge as number)}
                </span>
              </div>
            )}
            {targets.target_ee != null && (
              <div className="text-center">
                <span className="block text-[10px] text-slate-400">EE</span>
                <span className="font-mono font-semibold text-emerald-600">
                  {formatINRCompact.format(targets.target_ee as number)}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Account Value / RPT context */}
      {(alert.account_value_used !== null || alert.rpt_pct_used !== null) && (
        <p className="text-[10px] text-slate-400 mb-3">
          {alert.account_value_used !== null && (
            <span>AV: {formatINRCompact.format(alert.account_value_used)}</span>
          )}
          {alert.account_value_used !== null && alert.rpt_pct_used !== null && (
            <span className="mx-1.5">|</span>
          )}
          {alert.rpt_pct_used !== null && <span>RPT: {alert.rpt_pct_used}%</span>}
        </p>
      )}

      {/* Action text */}
      {alert.action_text && (
        <p className="text-xs text-slate-600 italic mb-3 line-clamp-2">
          {alert.action_text}
        </p>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-2 pt-3 border-t border-slate-100">
        <button
          disabled={isActing}
          onClick={() => onAct(alert.id)}
          className="bg-emerald-600 text-white text-xs font-medium px-4 py-2 rounded-lg hover:bg-emerald-700 transition-colors disabled:opacity-50"
        >
          Take Trade
        </button>
        <button
          disabled={isActing}
          onClick={() => onDismiss(alert.id)}
          className="bg-white text-slate-500 text-xs font-medium px-4 py-2 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors disabled:opacity-50"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sell Signal Card
// ---------------------------------------------------------------------------

function SellAlertCard({
  alert,
  onAct,
  onDismiss,
  isActing,
}: {
  alert: ActionAlert;
  onAct: (id: number) => void;
  onDismiss: (id: number) => void;
  isActing: boolean;
}) {
  const style = SELL_ALERT_STYLE[alert.alert_type] || {
    border: "border-l-slate-400",
    badge: "bg-slate-500 text-white",
    badgeText: alert.alert_type,
  };

  return (
    <div
      className={`bg-white rounded-xl border border-slate-200 border-l-4 ${style.border} p-5 hover:border-slate-300 transition-colors`}
    >
      {/* Header: Symbol + Type Badge */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-base font-bold text-slate-800 tracking-wide">
            {alert.symbol}
          </span>
          <span
            className={`${style.badge} rounded px-2 py-0.5 text-xs font-bold uppercase`}
          >
            {style.badgeText}
          </span>
        </div>
        {alert.trade_id !== null && (
          <span className="text-[10px] text-slate-400 font-mono">
            Trade #{alert.trade_id}
          </span>
        )}
      </div>

      {/* Price + Target Metrics */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs mb-3">
        {alert.current_price !== null && (
          <div>
            <span className="text-slate-400">CMP</span>
            <span className="ml-1.5 font-mono font-semibold text-slate-700">
              {formatINR.format(alert.current_price)}
            </span>
          </div>
        )}
        {alert.target_level !== null && (
          <div>
            <span className="text-slate-400">Target</span>
            <span className="ml-1.5 font-mono font-semibold text-emerald-600">
              {formatINR.format(alert.target_level)}
            </span>
          </div>
        )}
        {alert.exit_qty !== null && (
          <div>
            <span className="text-slate-400">Exit Qty</span>
            <span className="ml-1.5 font-mono font-semibold text-slate-700">
              {alert.exit_qty}
            </span>
          </div>
        )}
        {alert.exit_pct !== null && (
          <div>
            <span className="text-slate-400">Exit %</span>
            <span className="ml-1.5 font-mono font-semibold text-slate-700">
              {alert.exit_pct}%
            </span>
          </div>
        )}
        {alert.remaining_qty_after !== null && (
          <div>
            <span className="text-slate-400">Remaining</span>
            <span className="ml-1.5 font-mono font-semibold text-slate-700">
              {alert.remaining_qty_after}
            </span>
          </div>
        )}
      </div>

      {/* Action text */}
      {alert.action_text && (
        <div
          className={`rounded-lg px-3 py-2 mb-3 text-xs font-medium ${
            alert.alert_type === "SL_HIT"
              ? "bg-red-50 text-red-700"
              : "bg-amber-50 text-amber-700"
          }`}
        >
          {alert.action_text}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-2 pt-3 border-t border-slate-100">
        <button
          disabled={isActing}
          onClick={() => onAct(alert.id)}
          className={`text-white text-xs font-medium px-4 py-2 rounded-lg transition-colors disabled:opacity-50 ${
            alert.alert_type === "SL_HIT"
              ? "bg-red-600 hover:bg-red-700"
              : "bg-teal-600 hover:bg-teal-700"
          }`}
        >
          Execute Exit
        </button>
        <button
          disabled={isActing}
          onClick={() => onDismiss(alert.id)}
          className="bg-white text-slate-500 text-xs font-medium px-4 py-2 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors disabled:opacity-50"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Empty State
// ---------------------------------------------------------------------------

function EmptyState({ message, icon }: { message: string; icon: string }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-10 text-center col-span-full">
      <div className="text-4xl mb-3 text-slate-300">{icon}</div>
      <p className="text-sm text-slate-400">{message}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function ActionsPage() {
  // --- State ---
  const [alerts, setAlerts] = useState<ActionAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [actingIds, setActingIds] = useState<Set<number>>(new Set());
  const [lastChecked, setLastChecked] = useState<string | null>(null);

  // Controls
  const [accountValue, setAccountValue] = useState(DEFAULT_ACCOUNT_VALUE);
  const [rptPct, setRptPct] = useState(DEFAULT_RPT_PCT);

  // --- Derived data ---
  const buyAlerts = alerts.filter(
    (a) => a.alert_category === "BUY" && a.status === "NEW"
  );
  const sellAlerts = alerts.filter(
    (a) => a.alert_category === "SELL" && a.status === "NEW"
  );

  // Separate critical (SL_HIT) from profit-taking sell alerts for ordering
  const criticalSellAlerts = sellAlerts.filter((a) => a.alert_type === "SL_HIT");
  const profitSellAlerts = sellAlerts.filter((a) => a.alert_type !== "SL_HIT");

  // --- Data fetching ---
  const fetchAlerts = useCallback(async () => {
    try {
      setError(null);
      const data = await getActionAlerts(undefined, "NEW");
      setAlerts(data);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to fetch action alerts";
      setError(message);
      toast.error("Failed to load action alerts");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchDefaults = useCallback(async () => {
    try {
      const stance = await getLatestStance();
      if (stance) {
        if (stance.rpt_pct !== null) {
          setRptPct(stance.rpt_pct);
        }
      }
    } catch {
      // Silently fail — defaults are acceptable
    }
  }, []);

  useEffect(() => {
    fetchAlerts();
    fetchDefaults();
  }, [fetchAlerts, fetchDefaults]);

  // --- Handlers ---

  async function handleRefreshPrices() {
    setRefreshing(true);
    try {
      const result = await checkPrices(accountValue, rptPct);
      setLastChecked(result.last_checked);

      const totalAlerts = result.buy_alerts.length + result.sell_alerts.length;
      if (totalAlerts > 0) {
        toast.success(
          `${totalAlerts} alert${totalAlerts !== 1 ? "s" : ""} generated (${result.prices_fetched} prices checked)`
        );
      } else {
        toast.info(
          `No new signals. ${result.prices_fetched} prices checked.`
        );
      }

      // Re-fetch all alerts to get the updated list
      await fetchAlerts();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to check prices";
      toast.error(message);
    } finally {
      setRefreshing(false);
    }
  }

  async function handleAct(id: number) {
    setActingIds((prev) => new Set(prev).add(id));
    try {
      await actOnAlert(id);
      const alert = alerts.find((a) => a.id === id);
      toast.success(
        `${alert?.symbol ?? "Alert"} — ${alert?.alert_category === "BUY" ? "Trade taken" : "Exit executed"}`
      );
      await fetchAlerts();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to act on alert";
      toast.error(message);
    } finally {
      setActingIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  }

  async function handleDismiss(id: number) {
    setActingIds((prev) => new Set(prev).add(id));
    try {
      await dismissAlert(id);
      const alert = alerts.find((a) => a.id === id);
      toast.success(`${alert?.symbol ?? "Alert"} dismissed`);
      await fetchAlerts();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to dismiss alert";
      toast.error(message);
    } finally {
      setActingIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  }

  // --- Input classes (consistent with other pages) ---
  const inputClass =
    "w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none font-mono";
  const labelClass = "text-xs text-slate-500 mb-1 block font-medium";

  // --- Render ---

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
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-400 font-mono tabular-nums">
            {buyAlerts.length} buy / {sellAlerts.length} sell
          </span>
        </div>
      </div>

      {/* Info Banner */}
      <InfoBanner
        title="Quick Reference — Action Alert Terms"
        storageKey="actions"
      >
        <Term label="Trigger Break">
          Stock price breaks above the trigger level set in the watchlist. Entry
          signal.
        </Term>
        <Term label="SL Hit">
          Current price has fallen below the stop-loss. Mandatory full exit.
        </Term>
        <Term label="2R Target">
          Price reached 2x the risk (TRP). Exit 20% of position.
        </Term>
        <Term label="NE (Normal Exit)">
          Price reached 4x TRP. Exit another 20% of position.
        </Term>
        <Term label="GE (Great Exit)">
          Price reached 8x TRP. Exit 40% of position.
        </Term>
        <Term label="EE (Excellent Exit)">
          Price reached 12x TRP. Exit 80% of remaining position.
        </Term>
        <Term label="Exit Framework">
          2R = 20% out, NE = 20% out, GE = 40% out, EE = 80% out. Remaining
          rides with trailing stop.
        </Term>
      </InfoBanner>

      {/* Controls Bar */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="flex flex-wrap items-end gap-4">
          <div className="w-40">
            <label className={labelClass}>Account Value</label>
            <input
              type="number"
              step="10000"
              className={inputClass}
              value={accountValue}
              onChange={(e) => setAccountValue(Number(e.target.value))}
            />
          </div>
          <div className="w-28">
            <label className={labelClass}>RPT %</label>
            <input
              type="number"
              step="0.1"
              min="0.1"
              max="2.0"
              className={inputClass}
              value={rptPct}
              onChange={(e) => setRptPct(Number(e.target.value))}
            />
          </div>
          <button
            onClick={handleRefreshPrices}
            disabled={refreshing}
            className="bg-teal-600 text-white font-medium px-5 py-2 rounded-lg hover:bg-teal-700 transition-colors text-sm disabled:opacity-50 flex items-center gap-2"
          >
            {refreshing ? (
              <>
                <svg
                  className="animate-spin h-4 w-4"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Checking...
              </>
            ) : (
              "Refresh Prices"
            )}
          </button>
          {lastChecked && (
            <span className="text-xs text-slate-400 self-center">
              Last checked: {formatTime(lastChecked)}
            </span>
          )}
          <div className="ml-auto text-xs text-slate-400 self-center">
            AV:{" "}
            <span className="font-mono text-slate-600">
              {formatINRCompact.format(accountValue)}
            </span>
            <span className="mx-1.5">|</span>
            RPT:{" "}
            <span className="font-mono text-slate-600">{rptPct}%</span>
          </div>
        </div>
      </div>

      {/* Error state */}
      {error && !loading && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <p className="text-sm text-red-600 font-medium mb-2">
            Failed to load action alerts
          </p>
          <p className="text-xs text-red-400 mb-3">{error}</p>
          <button
            onClick={() => {
              setLoading(true);
              fetchAlerts();
            }}
            className="bg-red-600 text-white text-xs font-medium px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* ============================================================= */}
      {/* BUY SIGNALS SECTION                                            */}
      {/* ============================================================= */}
      <div>
        <div className="flex items-center gap-3 mb-4">
          <div className="bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-2.5 flex items-center gap-2">
            <span className="text-sm font-bold text-emerald-700">
              BUY SIGNALS
            </span>
            <span className="text-xs text-slate-400 font-mono">
              ({buyAlerts.length})
            </span>
          </div>
          {!loading && buyAlerts.length > 0 && (
            <p className="text-xs text-slate-400">
              Stocks breaking above trigger levels. Review and take trade.
            </p>
          )}
        </div>

        {loading && <SectionSkeleton count={3} />}

        {!loading && !error && buyAlerts.length === 0 && (
          <EmptyState
            icon="📡"
            message="No buy signals right now. Click Refresh Prices to scan for trigger breaks."
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

      {/* ============================================================= */}
      {/* SELL SIGNALS SECTION                                           */}
      {/* ============================================================= */}
      <div>
        <div className="flex items-center gap-3 mb-4">
          <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-2.5 flex items-center gap-2">
            <span className="text-sm font-bold text-red-700">
              SELL SIGNALS
            </span>
            <span className="text-xs text-slate-400 font-mono">
              ({sellAlerts.length})
            </span>
          </div>
          {!loading && sellAlerts.length > 0 && (
            <p className="text-xs text-slate-400">
              Active trades hitting targets or stop-losses. Execute exits.
            </p>
          )}
        </div>

        {loading && <SectionSkeleton count={2} />}

        {!loading && !error && sellAlerts.length === 0 && (
          <EmptyState
            icon="🛡"
            message="No sell signals. All positions within normal range."
          />
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
    </div>
  );
}
