"use client";

import { useState } from "react";

export function LearnSection() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-slate-50/50 transition-colors"
      >
        <span className="text-sm font-semibold text-slate-700 flex items-center gap-2">
          <span className="text-base">📖</span> Learn: How Actions Work
        </span>
        <svg
          className={`w-4 h-4 text-slate-400 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {isOpen && (
        <div className="px-5 pb-5 text-sm text-slate-600 leading-relaxed space-y-4 border-t border-slate-100 pt-4">
          <div>
            <h4 className="font-semibold text-slate-700 mb-1">
              What are Actions?
            </h4>
            <p className="text-xs text-slate-500">
              Actions are actionable BUY and SELL signals generated when the
              system checks live prices against your watchlist. A BUY signal
              appears when a stock breaks above its trigger level. A SELL signal
              appears when an active trade hits a stop loss or profit target.
            </p>
          </div>

          <div>
            <h4 className="font-semibold text-slate-700 mb-1">
              The Exit Framework
            </h4>
            <p className="text-xs text-slate-500 mb-2">
              The Champion Trader method uses a staged exit plan to lock in
              profits progressively:
            </p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              <div className="bg-slate-50 rounded-lg p-2.5 text-center">
                <p className="text-[10px] text-slate-400 uppercase font-medium">
                  2R Target
                </p>
                <p className="text-xs font-bold text-amber-600 mt-0.5">
                  Exit 20%
                </p>
                <p className="text-[10px] text-slate-400">2x risk distance</p>
              </div>
              <div className="bg-slate-50 rounded-lg p-2.5 text-center">
                <p className="text-[10px] text-slate-400 uppercase font-medium">
                  Normal Exit
                </p>
                <p className="text-xs font-bold text-amber-600 mt-0.5">
                  Exit 20%
                </p>
                <p className="text-[10px] text-slate-400">
                  4x True Range % from entry
                </p>
              </div>
              <div className="bg-slate-50 rounded-lg p-2.5 text-center">
                <p className="text-[10px] text-slate-400 uppercase font-medium">
                  Great Exit
                </p>
                <p className="text-xs font-bold text-teal-600 mt-0.5">
                  Exit 40%
                </p>
                <p className="text-[10px] text-slate-400">
                  8x True Range % from entry
                </p>
              </div>
              <div className="bg-slate-50 rounded-lg p-2.5 text-center">
                <p className="text-[10px] text-slate-400 uppercase font-medium">
                  Excellent Exit
                </p>
                <p className="text-xs font-bold text-emerald-600 mt-0.5">
                  Exit 80%
                </p>
                <p className="text-[10px] text-slate-400">
                  12x True Range % from entry
                </p>
              </div>
            </div>
            <p className="text-[10px] text-slate-400 mt-1.5">
              Any remaining position rides with a trailing stop loss.
            </p>
          </div>

          <div>
            <h4 className="font-semibold text-slate-700 mb-1">
              What does &ldquo;Refresh Prices&rdquo; do?
            </h4>
            <p className="text-xs text-slate-500">
              It fetches live market prices for all stocks on your watchlist and
              active trades, then compares them against trigger levels, stop
              losses, and exit targets to generate any new alerts.
            </p>
          </div>

          <div>
            <h4 className="font-semibold text-slate-700 mb-1">
              When to check Actions
            </h4>
            <p className="text-xs text-slate-500">
              Check during market hours (9:15 AM - 3:30 PM IST). The Champion
              Trader method specifically recommends taking entries in the
              <span className="font-semibold text-slate-700">
                {" "}
                last 30 minutes{" "}
              </span>
              of the session (3:00 - 3:30 PM) to confirm the breakout holds.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
