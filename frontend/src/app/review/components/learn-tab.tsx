"use client";

import { useState } from "react";
import {
  Section1SwingTrading,
  Section2FourStages,
  Section3Scanners,
  Section4BasePattern,
  Section5WatchlistSystem,
  Section6EntryRules,
} from "./methodology-content";
import {
  Section7PositionSizing,
  Section8StopLoss,
  Section9TakingProfits,
  Section10RiskManagement,
  Section11DailyRoutine,
  Section12WeeklyJournal,
  MethodologySummary,
} from "./methodology-content-part2";

// ---------------------------------------------------------------------------
// Table of Contents data
// ---------------------------------------------------------------------------

const TOC_ITEMS = [
  { id: "swing-trading", label: "What is Swing Trading?" },
  { id: "four-stages", label: "The 4 Stages of a Stock" },
  { id: "scanners", label: "How We Find Stocks (Scanners)" },
  { id: "base-pattern", label: "The Base Pattern" },
  { id: "watchlist-system", label: "Watchlist System" },
  { id: "entry-rules", label: "How We Buy (Entry Rules)" },
  { id: "position-sizing", label: "Position Sizing" },
  { id: "stop-loss", label: "Stop Loss (Protecting Yourself)" },
  { id: "taking-profits", label: "Taking Profits (Exits)" },
  { id: "risk-management", label: "Risk Management" },
  { id: "daily-routine", label: "The Daily Routine" },
  { id: "weekly-journal", label: "The Weekly Journal" },
] as const;

// ---------------------------------------------------------------------------
// Learn Tab
// ---------------------------------------------------------------------------

export function LearnTab() {
  const [activeToc, setActiveToc] = useState<string | null>(null);

  function scrollToSection(id: string) {
    setActiveToc(id);
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-base font-semibold text-slate-800">
          The Champion Trader Methodology
        </h2>
        <p className="text-sm text-slate-500 mt-0.5">
          A complete beginner-friendly guide to how we trade. No jargon, just clarity.
        </p>
      </div>

      {/* Introduction Card */}
      <div className="bg-teal-50 border border-teal-200 rounded-xl p-6">
        <p className="text-base font-semibold text-teal-800 mb-2">
          Welcome! This page explains everything you need to know.
        </p>
        <p className="text-sm text-teal-700 leading-relaxed">
          Imagine you have never traded a single stock in your life. This guide
          will walk you through the entire Champion Trader system step by step
          -- from finding good stocks, to buying them at the right time, to
          knowing exactly when to sell. Every concept uses simple words, real
          numbers, and visual examples.
        </p>
      </div>

      {/* Table of Contents */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h3 className="text-sm font-semibold text-slate-800 uppercase tracking-wider mb-4">
          Table of Contents
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
          {TOC_ITEMS.map((item, index) => (
            <button
              key={item.id}
              onClick={() => scrollToSection(item.id)}
              className={`text-left flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                activeToc === item.id
                  ? "bg-teal-50 text-teal-700 font-medium"
                  : "text-slate-600 hover:bg-slate-50 hover:text-slate-800"
              }`}
            >
              <span className="flex-shrink-0 w-6 h-6 rounded bg-slate-100 text-slate-500 flex items-center justify-center text-xs font-bold">
                {index + 1}
              </span>
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {/* All 12 Methodology Sections */}
      <Section1SwingTrading />
      <Section2FourStages />
      <Section3Scanners />
      <Section4BasePattern />
      <Section5WatchlistSystem />
      <Section6EntryRules />
      <Section7PositionSizing />
      <Section8StopLoss />
      <Section9TakingProfits />
      <Section10RiskManagement />
      <Section11DailyRoutine />
      <Section12WeeklyJournal />

      {/* Final Summary */}
      <MethodologySummary />

      {/* Spacer for comfortable scrolling */}
      <div className="h-8" />
    </div>
  );
}
