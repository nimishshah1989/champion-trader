"use client";

import { useEffect, useState, useCallback } from "react";
import { getAlerts, getUnreadAlertCount, markAlertRead, markAllAlertsRead, type AppAlert } from "@/lib/api";

const SEVERITY_STYLES: Record<string, { dot: string; bg: string }> = {
  critical: { dot: "bg-red-500", bg: "bg-red-50" },
  warning: { dot: "bg-amber-500", bg: "bg-amber-50" },
  info: { dot: "bg-teal-500", bg: "bg-teal-50" },
};

export function AlertBell() {
  const [unreadCount, setUnreadCount] = useState(0);
  const [alerts, setAlerts] = useState<AppAlert[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const fetchCount = useCallback(async () => {
    try {
      const data = await getUnreadAlertCount();
      setUnreadCount(data.count);
    } catch {
      // Silently fail — alerts are not critical
    }
  }, []);

  useEffect(() => {
    fetchCount();
    const interval = setInterval(fetchCount, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, [fetchCount]);

  async function handleOpen() {
    if (open) {
      setOpen(false);
      return;
    }
    setOpen(true);
    setLoading(true);
    try {
      const data = await getAlerts();
      setAlerts(data);
    } catch {
      setAlerts([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleMarkRead(id: number) {
    try {
      await markAlertRead(id);
      setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, is_read: true } : a)));
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch {
      // ignore
    }
  }

  async function handleMarkAllRead() {
    try {
      await markAllAlertsRead();
      setAlerts((prev) => prev.map((a) => ({ ...a, is_read: true })));
      setUnreadCount(0);
    } catch {
      // ignore
    }
  }

  function formatTime(dateStr: string | null): string {
    if (!dateStr) return "";
    const d = new Date(dateStr + "Z");
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return "just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  }

  return (
    <div className="relative">
      {/* Bell button */}
      <button
        onClick={handleOpen}
        className="relative p-2 rounded-lg hover:bg-slate-100 transition-colors"
        aria-label="Alerts"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="text-slate-600"
        >
          <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
          <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 bg-red-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {open && (
        <>
          {/* Backdrop */}
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />

          {/* Panel */}
          <div className="absolute right-0 top-full mt-2 w-96 bg-white rounded-xl border border-slate-200 shadow-lg z-50 overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-800">Alerts</h3>
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  className="text-[11px] text-teal-600 hover:text-teal-700 font-medium"
                >
                  Mark all read
                </button>
              )}
            </div>

            <div className="max-h-96 overflow-y-auto">
              {loading ? (
                <div className="p-6 text-center">
                  <p className="text-sm text-slate-400">Loading alerts...</p>
                </div>
              ) : alerts.length === 0 ? (
                <div className="p-6 text-center">
                  <p className="text-sm text-slate-400">No alerts yet</p>
                  <p className="text-xs text-slate-300 mt-1">Alerts from TradingView webhooks will appear here</p>
                </div>
              ) : (
                alerts.slice(0, 30).map((alert) => {
                  const style = SEVERITY_STYLES[alert.severity] ?? SEVERITY_STYLES.info;
                  return (
                    <button
                      key={alert.id}
                      onClick={() => !alert.is_read && handleMarkRead(alert.id)}
                      className={`w-full text-left px-4 py-3 border-b border-slate-50 hover:bg-slate-50/50 transition-colors ${
                        !alert.is_read ? "bg-slate-50" : ""
                      }`}
                    >
                      <div className="flex items-start gap-2.5">
                        <span className={`${style.dot} w-2 h-2 rounded-full mt-1.5 shrink-0`} />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-2">
                            <p className={`text-xs font-semibold truncate ${!alert.is_read ? "text-slate-800" : "text-slate-500"}`}>
                              {alert.title}
                            </p>
                            <span className="text-[10px] text-slate-400 shrink-0">
                              {formatTime(alert.created_at)}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">{alert.message}</p>
                          {alert.symbol && (
                            <span className="inline-block mt-1 text-[10px] font-mono font-semibold text-teal-600 bg-teal-50 rounded px-1.5 py-0.5">
                              {alert.symbol}
                            </span>
                          )}
                        </div>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
