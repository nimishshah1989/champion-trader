"use client";

import { useState, useEffect } from "react";

// ---------------------------------------------------------------------------
// Pipeline Learn Section — collapsible educational content
// ---------------------------------------------------------------------------

const STORAGE_KEY = "pipeline-learn-collapsed";

export function PipelineLearn() {
  const [isOpen, setIsOpen] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "expanded") {
      setIsOpen(true);
    }
    setMounted(true);
  }, []);

  function toggle() {
    const next = !isOpen;
    setIsOpen(next);
    localStorage.setItem(STORAGE_KEY, next ? "expanded" : "collapsed");
  }

  if (!mounted) return null;

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <button
        type="button"
        onClick={toggle}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-50/50 transition-colors"
      >
        <span className="text-sm font-semibold text-slate-800">
          Learn: How the Pipeline Works
        </span>
        <svg
          className={`w-4 h-4 text-slate-400 transition-transform duration-200 ${
            isOpen ? "rotate-180" : ""
          }`}
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
        <div className="px-5 pb-5 space-y-5">
          {/* What the Pipeline does */}
          <Section title="What is the Pipeline?">
            <p>
              The Pipeline is your unified stock discovery and monitoring board. It replaces
              the separate Scanner and Watchlist pages by combining them into a single workflow:
              scan for patterns, auto-categorize results, and track stocks as they mature toward
              entry.
            </p>
          </Section>

          {/* Scan types */}
          <Section title="What does each scan type detect?">
            <dl className="space-y-2">
              <Definition term="Positive Pivotal Candle (PPC)">
                A bullish accumulation signal. The stock&apos;s daily range expands 1.5x or more
                above its 20-day average, the close is in the upper 60% of the range, volume
                spikes 1.5x or more above average, and the candle is green. This indicates
                institutional buying interest.
              </Definition>
              <Definition term="Negative Pivotal Candle (NPC)">
                A bearish distribution signal (mirror of PPC). The daily range expands 1.5x+,
                the close is in the lower 40% of the range, volume spikes 1.5x+, and the candle
                is red. This indicates institutional selling pressure.
              </Definition>
              <Definition term="Base Contraction">
                A volatility squeeze pattern. The stock&apos;s Average True Range (ATR) is
                declining, candles are narrowing, and price is consolidating near resistance.
                The stock is coiling before a potential breakout. Requires a minimum 20-bar base.
              </Definition>
            </dl>
          </Section>

          {/* Buckets */}
          <Section title="What do READY, NEAR, and AWAY mean?">
            <dl className="space-y-2">
              <Definition term="READY">
                Stocks with a mature base (20+ bars), a defined trigger level, and strong
                setup characteristics. These are highest priority and may be actionable within
                days. Set price alerts for READY stocks.
              </Definition>
              <Definition term="NEAR">
                Stocks with a maturing base (15+ bars) and a trigger forming. Expected to
                become READY within 1-2 weeks. Check these daily during market hours.
              </Definition>
              <Definition term="AWAY">
                Stocks in an early-stage base that are worth watching but are not ready for
                entry. They need more consolidation time. Monitor these weekly.
              </Definition>
            </dl>
          </Section>

          {/* Auto-flow */}
          <Section title="How does auto-flow work?">
            <ol className="list-decimal list-inside space-y-1.5 text-slate-600">
              <li>
                Run a scan to detect Positive Pivotal Candle, Negative Pivotal Candle, and
                Base Contraction patterns across ~500 NIFTY stocks.
              </li>
              <li>
                Each detected signal is automatically categorized into READY, NEAR, or AWAY
                based on the stock&apos;s base maturity, stage, and signal strength.
              </li>
              <li>
                Stocks already in your watchlist remain in their current bucket. New
                discoveries from the scan auto-populate into the appropriate column.
              </li>
              <li>
                As a stock&apos;s base matures, promote it from AWAY to NEAR to READY using the
                move buttons on each card.
              </li>
              <li>
                When a READY stock triggers (price clears the trigger level), navigate to the
                Position Calculator to plan your entry with proper sizing.
              </li>
            </ol>
          </Section>

          {/* Position sizing note */}
          <div className="bg-teal-50 border border-teal-200 rounded-lg px-4 py-3">
            <p className="text-xs text-teal-700">
              <span className="font-semibold">Position sizing on cards:</span> Each card
              shows a calculated Position Size and Half Quantity based on your current Account
              Value and Risk Per Trade settings. These use the stock&apos;s trigger level as
              entry price and True Range Percentage as stop-loss distance. Adjust your settings
              in the gear icon to update all calculations.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Internal sub-components
// ---------------------------------------------------------------------------

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h4 className="text-sm font-semibold text-slate-700 mb-1.5">{title}</h4>
      <div className="text-xs text-slate-600 leading-relaxed">{children}</div>
    </div>
  );
}

function Definition({
  term,
  children,
}: {
  term: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <dt className="text-xs font-semibold text-slate-700">{term}</dt>
      <dd className="text-xs text-slate-600 leading-relaxed ml-0">{children}</dd>
    </div>
  );
}
