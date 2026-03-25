"use client";

import { useEffect, useState } from "react";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

export function formatTime(isoStr: string): string {
  try {
    return new Date(isoStr).toLocaleString("en-IN", {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });
  } catch (err) {
    console.error("Failed to parse date string:", err);
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

export type MonitorStatus =
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

export function SpinnerIcon() {
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

export function LiveMonitorBadge() {
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
