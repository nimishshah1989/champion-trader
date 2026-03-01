"use client";

import { useState } from "react";

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
// Reusable sub-components
// ---------------------------------------------------------------------------

function SectionCard({
  id,
  number,
  title,
  children,
}: {
  id: string;
  number: number;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-24">
      <div className="bg-white rounded-xl border border-slate-200 p-6 md:p-8">
        <div className="flex items-center gap-3 mb-6">
          <span className="flex-shrink-0 w-8 h-8 rounded-lg bg-teal-600 flex items-center justify-center text-white font-bold text-sm">
            {number}
          </span>
          <h2 className="text-lg font-semibold text-slate-800">{title}</h2>
        </div>
        {children}
      </div>
    </section>
  );
}

function Callout({
  type,
  children,
}: {
  type: "tip" | "warning" | "danger";
  children: React.ReactNode;
}) {
  const styles = {
    tip: "border-l-teal-500 bg-teal-50",
    warning: "border-l-amber-500 bg-amber-50",
    danger: "border-l-red-500 bg-red-50",
  };
  const icons = {
    tip: "Tip",
    warning: "Caution",
    danger: "Never Do This",
  };
  const textColors = {
    tip: "text-teal-800",
    warning: "text-amber-800",
    danger: "text-red-800",
  };

  return (
    <div className={`border-l-4 ${styles[type]} rounded-r-lg p-4 my-4`}>
      <p className={`text-xs font-bold uppercase tracking-wider ${textColors[type]} mb-1`}>
        {icons[type]}
      </p>
      <p className={`text-sm ${textColors[type]}`}>{children}</p>
    </div>
  );
}

function StepFlow({ steps }: { steps: { label: string; detail: string }[] }) {
  return (
    <div className="space-y-0">
      {steps.map((step, index) => (
        <div key={index} className="flex gap-4">
          {/* Vertical connector */}
          <div className="flex flex-col items-center">
            <div className="w-8 h-8 rounded-full bg-teal-600 text-white flex items-center justify-center text-sm font-bold flex-shrink-0">
              {index + 1}
            </div>
            {index < steps.length - 1 && (
              <div className="w-0.5 h-full bg-teal-200 min-h-[24px]" />
            )}
          </div>
          <div className="pb-6">
            <p className="text-sm font-semibold text-slate-800">{step.label}</p>
            <p className="text-sm text-slate-600 mt-0.5">{step.detail}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Methodology Page
// ---------------------------------------------------------------------------

export default function MethodologyPage() {
  const [activeToc, setActiveToc] = useState<string | null>(null);

  const scrollToSection = (id: string) => {
    setActiveToc(id);
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-slate-800">
          The Champion Trader Methodology
        </h1>
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
          numbers, and visual examples. Take your time. Read it section by
          section.
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

      {/* ================================================================ */}
      {/* SECTION 1 — What is Swing Trading? */}
      {/* ================================================================ */}
      <SectionCard id="swing-trading" number={1} title="What is Swing Trading?">
        <p className="text-sm text-slate-600 leading-relaxed mb-4">
          Think of the stock market like an ocean with waves. Some people try to
          ride tiny ripples (day traders -- they buy and sell within minutes).
          Others sit on a boat for years waiting for the tide to rise
          (long-term investors). We do something in the middle:
        </p>
        <p className="text-base font-semibold text-teal-700 mb-6">
          We catch medium-sized waves that last 1 to 4 weeks.
        </p>

        {/* Visual comparison */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {/* Day Trading */}
          <div className="border border-slate-200 rounded-xl p-4 text-center">
            <div className="flex justify-center gap-0.5 mb-3 h-12 items-end">
              {[3, 5, 2, 6, 1, 4, 3, 7, 2, 5, 1, 6, 3, 4, 2].map((h, i) => (
                <div
                  key={i}
                  className="w-1.5 bg-slate-300 rounded-t"
                  style={{ height: `${h * 6}px` }}
                />
              ))}
            </div>
            <p className="text-sm font-semibold text-slate-400">Day Trading</p>
            <p className="text-xs text-slate-400 mt-1">Minutes to hours</p>
            <span className="inline-block mt-2 bg-red-50 text-red-600 rounded-full px-3 py-0.5 text-xs font-medium">
              Not us
            </span>
          </div>

          {/* Swing Trading */}
          <div className="border-2 border-teal-500 rounded-xl p-4 text-center bg-teal-50/30">
            <div className="flex justify-center gap-0.5 mb-3 h-12 items-end">
              {[2, 3, 4, 5, 7, 8, 9, 10, 9, 8, 7, 5, 4, 3, 2].map((h, i) => (
                <div
                  key={i}
                  className="w-1.5 bg-teal-500 rounded-t"
                  style={{ height: `${h * 4.5}px` }}
                />
              ))}
            </div>
            <p className="text-sm font-bold text-teal-700">Swing Trading</p>
            <p className="text-xs text-teal-600 mt-1">1 to 4 weeks</p>
            <span className="inline-block mt-2 bg-teal-100 text-teal-700 rounded-full px-3 py-0.5 text-xs font-bold">
              This is us!
            </span>
          </div>

          {/* Investing */}
          <div className="border border-slate-200 rounded-xl p-4 text-center">
            <div className="flex justify-center gap-0.5 mb-3 h-12 items-end">
              {[2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9].map((h, i) => (
                <div
                  key={i}
                  className="w-1.5 bg-slate-300 rounded-t"
                  style={{ height: `${h * 5}px` }}
                />
              ))}
            </div>
            <p className="text-sm font-semibold text-slate-400">Investing</p>
            <p className="text-xs text-slate-400 mt-1">Months to years</p>
            <span className="inline-block mt-2 bg-slate-100 text-slate-500 rounded-full px-3 py-0.5 text-xs font-medium">
              Not us
            </span>
          </div>
        </div>

        <Callout type="tip">
          Our goal with each trade: catch a price move of 10% to 30%. Not every
          trade will hit that, but that is what we aim for. Small, focused
          bets with clear entry and exit rules.
        </Callout>
      </SectionCard>

      {/* ================================================================ */}
      {/* SECTION 2 — The 4 Stages (Weinstein) */}
      {/* ================================================================ */}
      <SectionCard id="four-stages" number={2} title="The 4 Stages of a Stock (Weinstein Stage Analysis)">
        <p className="text-sm text-slate-600 leading-relaxed mb-4">
          Every stock in the market goes through 4 stages, like the life of a
          wave. Think of it like an animal -- it sleeps, wakes up, runs, gets
          tired, and falls. The key to making money is buying at the right stage.
        </p>

        {/* Visual mountain/wave diagram */}
        <div className="bg-slate-50 rounded-xl p-6 mb-6">
          <p className="text-xs text-slate-400 font-semibold uppercase tracking-wider mb-4 text-center">
            The Stock Lifecycle -- Where to Buy and Where to Avoid
          </p>
          <div className="flex items-end gap-0 h-56 md:h-64 relative">
            {/* Stage 1 - Sleeping (flat left) */}
            <div className="flex-1 flex flex-col justify-end items-stretch">
              <div className="bg-slate-300 rounded-tl-lg h-16 flex items-center justify-center border-r border-white">
                <div className="text-center px-1">
                  <p className="text-xs font-bold text-slate-700">Stage 1</p>
                  <p className="text-[10px] text-slate-500">Sleeping</p>
                </div>
              </div>
            </div>

            {/* Stage 1 Breakout arrow zone */}
            <div className="flex-[0.5] flex flex-col justify-end items-stretch relative">
              <div className="absolute -top-8 left-1/2 -translate-x-1/2 whitespace-nowrap">
                <span className="text-[10px] font-bold text-amber-600 bg-amber-50 border border-amber-200 rounded px-2 py-0.5">
                  Breakout!
                </span>
              </div>
              <div className="bg-amber-400 h-28 flex items-center justify-center border-r border-white">
                <div className="text-center px-1">
                  <p className="text-[10px] font-bold text-amber-800">Wake Up</p>
                </div>
              </div>
            </div>

            {/* Stage 2 - Running (tall peak) */}
            <div className="flex-1 flex flex-col justify-end items-stretch relative">
              <div className="absolute -top-10 left-1/2 -translate-x-1/2 whitespace-nowrap">
                <span className="text-[10px] font-bold text-white bg-emerald-600 rounded px-2 py-1">
                  BUY HERE
                </span>
              </div>
              <div className="bg-emerald-500 rounded-t-xl h-48 md:h-56 flex items-center justify-center border-r border-white">
                <div className="text-center px-1">
                  <p className="text-xs font-bold text-white">Stage 2</p>
                  <p className="text-[10px] text-emerald-100">Running Up!</p>
                </div>
              </div>
            </div>

            {/* Stage 3 - Tired (medium, going down) */}
            <div className="flex-1 flex flex-col justify-end items-stretch relative">
              <div className="absolute -top-8 left-1/2 -translate-x-1/2 whitespace-nowrap">
                <span className="text-[10px] font-bold text-amber-700 bg-amber-100 border border-amber-300 rounded px-2 py-0.5">
                  DO NOT BUY
                </span>
              </div>
              <div className="bg-amber-400 rounded-t-lg h-32 flex items-center justify-center border-r border-white">
                <div className="text-center px-1">
                  <p className="text-xs font-bold text-amber-800">Stage 3</p>
                  <p className="text-[10px] text-amber-700">Getting Tired</p>
                </div>
              </div>
            </div>

            {/* Stage 4 - Falling (short, bad) */}
            <div className="flex-1 flex flex-col justify-end items-stretch relative">
              <div className="absolute -top-8 left-1/2 -translate-x-1/2 whitespace-nowrap">
                <span className="text-[10px] font-bold text-white bg-red-600 rounded px-2 py-0.5">
                  NEVER BUY
                </span>
              </div>
              <div className="bg-red-400 rounded-tr-lg h-12 flex items-center justify-center">
                <div className="text-center px-1">
                  <p className="text-xs font-bold text-red-800">Stage 4</p>
                  <p className="text-[10px] text-red-700">Falling</p>
                </div>
              </div>
            </div>
          </div>

          {/* Legend */}
          <div className="flex flex-wrap items-center justify-center gap-4 mt-4 text-xs">
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded bg-slate-300" />
              <span className="text-slate-500">Sideways (boring)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded bg-emerald-500" />
              <span className="text-slate-500">Running up (we buy here)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded bg-amber-400" />
              <span className="text-slate-500">Transition (caution)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded bg-red-400" />
              <span className="text-slate-500">Falling (avoid)</span>
            </div>
          </div>
        </div>

        {/* Stage explanations */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="border border-slate-200 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-3 h-3 rounded bg-slate-300" />
              <p className="text-sm font-semibold text-slate-800">Stage 1 -- Sleeping</p>
            </div>
            <p className="text-sm text-slate-600 leading-relaxed">
              The stock is moving sideways. Nothing exciting is happening. Like a
              cat napping on a couch -- nobody pays attention to it. The price
              just drifts left and right with no clear direction.
            </p>
          </div>
          <div className="border border-teal-200 bg-teal-50/30 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-3 h-3 rounded bg-emerald-500" />
              <p className="text-sm font-semibold text-teal-800">Stage 2 -- Running (WE BUY HERE)</p>
            </div>
            <p className="text-sm text-slate-600 leading-relaxed">
              The cat woke up and is running! The stock is moving upward with
              energy and volume. The price keeps making higher highs and higher
              lows. This is the ONLY stage where we buy.
            </p>
          </div>
          <div className="border border-amber-200 bg-amber-50/30 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-3 h-3 rounded bg-amber-400" />
              <p className="text-sm font-semibold text-amber-800">Stage 3 -- Getting Tired</p>
            </div>
            <p className="text-sm text-slate-600 leading-relaxed">
              The cat is slowing down, panting. The stock stops making new highs
              and starts moving sideways again at the top. It looks tempting
              because the price is high, but do NOT buy -- it is about to rest
              or fall.
            </p>
          </div>
          <div className="border border-red-200 bg-red-50/30 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-3 h-3 rounded bg-red-400" />
              <p className="text-sm font-semibold text-red-800">Stage 4 -- Falling</p>
            </div>
            <p className="text-sm text-slate-600 leading-relaxed">
              The cat fell off a cliff. The stock is going down, making lower
              lows. Never, ever buy a Stage 4 stock. It does not matter how
              &quot;cheap&quot; it looks -- it is cheap for a reason. Wait for it
              to finish falling and start a new Stage 1.
            </p>
          </div>
        </div>

        <Callout type="tip">
          The single most important rule: Only buy stocks in Stage 2. If you are
          not sure about the stage, skip it. There are always more opportunities
          tomorrow.
        </Callout>
      </SectionCard>

      {/* ================================================================ */}
      {/* SECTION 3 — The Scanners */}
      {/* ================================================================ */}
      <SectionCard id="scanners" number={3} title="How We Find Stocks to Buy (The Scanners)">
        <p className="text-sm text-slate-600 leading-relaxed mb-6">
          There are thousands of stocks in the market. We use special scans to
          filter down to just a handful that look promising. Think of these
          scanners as metal detectors on a beach -- they help us find the
          hidden gold.
        </p>

        {/* PPC */}
        <div className="border border-emerald-200 bg-emerald-50/30 rounded-xl p-5 mb-4">
          <div className="flex items-center gap-3 mb-3">
            <span className="bg-emerald-600 text-white text-xs font-bold px-2.5 py-1 rounded">
              PPC
            </span>
            <h4 className="text-sm font-semibold text-slate-800">
              Positive Pivotal Candle
            </h4>
          </div>
          <p className="text-sm text-slate-600 mb-4 leading-relaxed">
            Imagine a celebrity walks into a quiet room. Everyone turns to look.
            A PPC is exactly that moment for a stock. It is a big green candle --
            much bigger than normal -- that says &quot;something important just
            happened here!&quot;
          </p>
          {/* Visual candle representation */}
          <div className="bg-white rounded-lg p-4 border border-emerald-100">
            <p className="text-xs text-slate-400 mb-3 text-center font-medium">What a PPC looks like compared to normal candles</p>
            <div className="flex items-end justify-center gap-2 h-32">
              {/* Normal candles */}
              {[40, 35, 38, 42, 36].map((h, i) => (
                <div key={`n-${i}`} className="flex flex-col items-center">
                  <div
                    className={`w-5 rounded-sm ${i % 2 === 0 ? "bg-emerald-300" : "bg-red-300"}`}
                    style={{ height: `${h}px` }}
                  />
                  <p className="text-[9px] text-slate-300 mt-1">Normal</p>
                </div>
              ))}
              {/* PPC candle - big and green */}
              <div className="flex flex-col items-center mx-2">
                <div className="w-8 bg-emerald-600 rounded-sm" style={{ height: "100px" }} />
                <p className="text-[9px] text-emerald-600 font-bold mt-1">PPC!</p>
              </div>
              {/* After candles */}
              {[45, 48, 50].map((h, i) => (
                <div key={`a-${i}`} className="flex flex-col items-center">
                  <div
                    className="w-5 bg-emerald-300 rounded-sm"
                    style={{ height: `${h}px` }}
                  />
                  <p className="text-[9px] text-slate-300 mt-1">After</p>
                </div>
              ))}
            </div>
          </div>
          <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="bg-white rounded-lg p-3 border border-slate-100 text-center">
              <p className="text-xs text-slate-400">Size</p>
              <p className="text-sm font-semibold text-slate-800">1.5x bigger than normal</p>
            </div>
            <div className="bg-white rounded-lg p-3 border border-slate-100 text-center">
              <p className="text-xs text-slate-400">Close Position</p>
              <p className="text-sm font-semibold text-slate-800">Near the top of its range</p>
            </div>
            <div className="bg-white rounded-lg p-3 border border-slate-100 text-center">
              <p className="text-xs text-slate-400">Volume</p>
              <p className="text-sm font-semibold text-slate-800">Much higher than average</p>
            </div>
          </div>
        </div>

        {/* NPC */}
        <div className="border border-red-200 bg-red-50/30 rounded-xl p-5 mb-4">
          <div className="flex items-center gap-3 mb-3">
            <span className="bg-red-600 text-white text-xs font-bold px-2.5 py-1 rounded">
              NPC
            </span>
            <h4 className="text-sm font-semibold text-slate-800">
              Negative Pivotal Candle
            </h4>
          </div>
          <p className="text-sm text-slate-600 leading-relaxed">
            The opposite of a PPC. It is a big red candle -- like a fire alarm
            going off. Everyone is rushing to sell. This is a warning signal. If
            you see an NPC in a stock you own, pay close attention to your stop
            loss. If you see it in a stock you are watching, it means
            &quot;wait, do not buy yet.&quot;
          </p>
        </div>

        {/* Contraction */}
        <div className="border border-blue-200 bg-blue-50/30 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <span className="bg-blue-600 text-white text-xs font-bold px-2.5 py-1 rounded">
              CONTRACTION
            </span>
            <h4 className="text-sm font-semibold text-slate-800">
              Volatility Contraction (The Spring)
            </h4>
          </div>
          <p className="text-sm text-slate-600 mb-4 leading-relaxed">
            Imagine pressing a spring down. The more you compress it, the
            more explosive the release. Contraction is when a stock gets
            quieter and quieter -- the candles get smaller and smaller, and
            volume dries up. It is building energy for a big move.
          </p>
          {/* Visual spring compression */}
          <div className="bg-white rounded-lg p-4 border border-blue-100">
            <p className="text-xs text-slate-400 mb-3 text-center font-medium">Candles getting smaller = spring getting tighter</p>
            <div className="flex items-center justify-center gap-1.5 h-24">
              {[60, 50, 42, 35, 28, 22, 17, 13, 10, 8, 6].map((h, i) => (
                <div
                  key={i}
                  className="w-4 bg-blue-400 rounded-sm self-center"
                  style={{ height: `${h}px`, opacity: 0.4 + (i / 11) * 0.6 }}
                />
              ))}
              {/* The explosion */}
              <div className="mx-1 text-lg">
                ...
              </div>
              <div
                className="w-6 bg-emerald-500 rounded-sm self-end"
                style={{ height: "90px" }}
              />
              <p className="text-emerald-600 text-xs font-bold ml-1 self-start mt-2">
                SPRING!
              </p>
            </div>
          </div>
        </div>
      </SectionCard>

      {/* ================================================================ */}
      {/* SECTION 4 — The Base Pattern */}
      {/* ================================================================ */}
      <SectionCard id="base-pattern" number={4} title="The Base Pattern (Where Good Setups Form)">
        <p className="text-sm text-slate-600 leading-relaxed mb-4">
          Before a rocket launches, it sits on a launchpad. Before a stock
          explodes upward, it forms a &quot;base.&quot; A base is a sideways
          movement that lasts at least 20 trading days (about 4 weeks).
        </p>

        {/* Visual base pattern */}
        <div className="bg-slate-50 rounded-xl p-6 mb-6">
          <p className="text-xs text-slate-400 font-semibold uppercase tracking-wider mb-4 text-center">
            A Stock Forming a Base (Sideways for 20+ Days)
          </p>
          <div className="relative h-40 flex items-end">
            {/* Price came up before the base */}
            {[20, 30, 40, 55, 65, 72, 76, 78].map((h, i) => (
              <div
                key={`up-${i}`}
                className="flex-1 bg-emerald-400 mx-px rounded-t-sm"
                style={{ height: `${h}%` }}
              />
            ))}
            {/* The base - sideways */}
            {[
              78, 76, 74, 77, 75, 73, 76, 74, 75, 77, 74, 76, 75, 73, 76, 78,
              75, 74, 77, 76,
            ].map((h, i) => (
              <div
                key={`base-${i}`}
                className="flex-1 bg-blue-300 mx-px rounded-t-sm"
                style={{ height: `${h}%` }}
              />
            ))}
            {/* Breakout */}
            {[80, 85, 92, 97].map((h, i) => (
              <div
                key={`brk-${i}`}
                className="flex-1 bg-teal-500 mx-px rounded-t-sm"
                style={{ height: `${h}%` }}
              />
            ))}

            {/* Labels */}
            <div className="absolute top-0 left-[12%] text-[10px] text-emerald-600 font-semibold">
              Price moving up
            </div>
            <div className="absolute top-0 left-[38%] right-[20%] text-center">
              <div className="border-b-2 border-dashed border-blue-400 mb-1" />
              <p className="text-[10px] text-blue-600 font-semibold">The Base (20+ days sideways)</p>
            </div>
            <div className="absolute top-0 right-0 text-[10px] text-teal-600 font-bold">
              Breakout!
            </div>
          </div>
        </div>

        {/* What makes a good base */}
        <h4 className="text-sm font-semibold text-slate-800 mb-3">
          What makes a GOOD base? Think of a rocket launchpad:
        </h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
          <div className="flex items-start gap-3 bg-slate-50 rounded-lg p-3">
            <span className="flex-shrink-0 w-6 h-6 bg-emerald-100 text-emerald-700 rounded-full flex items-center justify-center text-xs font-bold">1</span>
            <div>
              <p className="text-sm font-medium text-slate-800">Smooth sideways movement</p>
              <p className="text-xs text-slate-500 mt-0.5">Not wild up-and-down swings, but a calm, tight channel.</p>
            </div>
          </div>
          <div className="flex items-start gap-3 bg-slate-50 rounded-lg p-3">
            <span className="flex-shrink-0 w-6 h-6 bg-emerald-100 text-emerald-700 rounded-full flex items-center justify-center text-xs font-bold">2</span>
            <div>
              <p className="text-sm font-medium text-slate-800">Big buyers accumulating</p>
              <p className="text-xs text-slate-500 mt-0.5">You might see PPC candles inside the base -- smart money quietly buying.</p>
            </div>
          </div>
          <div className="flex items-start gap-3 bg-slate-50 rounded-lg p-3">
            <span className="flex-shrink-0 w-6 h-6 bg-emerald-100 text-emerald-700 rounded-full flex items-center justify-center text-xs font-bold">3</span>
            <div>
              <p className="text-sm font-medium text-slate-800">Volume dries up on red days</p>
              <p className="text-xs text-slate-500 mt-0.5">When the stock drops a little, almost nobody is selling. That is good -- sellers are exhausted.</p>
            </div>
          </div>
          <div className="flex items-start gap-3 bg-slate-50 rounded-lg p-3">
            <span className="flex-shrink-0 w-6 h-6 bg-emerald-100 text-emerald-700 rounded-full flex items-center justify-center text-xs font-bold">4</span>
            <div>
              <p className="text-sm font-medium text-slate-800">Getting tighter (contraction)</p>
              <p className="text-xs text-slate-500 mt-0.5">The range gets narrower over time. The spring is compressing.</p>
            </div>
          </div>
        </div>

        <Callout type="tip">
          The longer and tighter the base, the more powerful the breakout. A
          stock that has been quiet for 30-40 days is building serious energy.
          Be patient.
        </Callout>
      </SectionCard>

      {/* ================================================================ */}
      {/* SECTION 5 — Watchlist System */}
      {/* ================================================================ */}
      <SectionCard id="watchlist-system" number={5} title="The Watchlist System (READY / NEAR / AWAY)">
        <p className="text-sm text-slate-600 leading-relaxed mb-6">
          Once we find interesting stocks through our scanners, we sort them
          into three buckets. Think of it like a traffic light system:
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {/* READY */}
          <div className="border-2 border-emerald-500 rounded-xl p-5 bg-emerald-50/30">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-4 h-4 rounded-full bg-emerald-500" />
              <h4 className="text-base font-bold text-emerald-700">READY</h4>
            </div>
            <p className="text-sm text-slate-600 leading-relaxed mb-3">
              Ready to launch! The stock has formed a good base, is in Stage 2,
              and the trigger level is set. If the price breaks above the trigger
              tomorrow, we buy.
            </p>
            <div className="bg-white rounded-lg p-3 border border-emerald-100">
              <p className="text-xs text-slate-400 mb-1">What you do:</p>
              <p className="text-xs text-emerald-700 font-medium">
                Set an alert on TradingView. Check it daily in the last 30
                minutes before close. Be ready to buy.
              </p>
            </div>
          </div>

          {/* NEAR */}
          <div className="border-2 border-amber-400 rounded-xl p-5 bg-amber-50/30">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-4 h-4 rounded-full bg-amber-500" />
              <h4 className="text-base font-bold text-amber-700">NEAR</h4>
            </div>
            <p className="text-sm text-slate-600 leading-relaxed mb-3">
              Almost ready. The base is forming nicely but needs a few more days.
              Maybe the contraction is not tight enough yet, or the volume pattern
              is not perfect.
            </p>
            <div className="bg-white rounded-lg p-3 border border-amber-100">
              <p className="text-xs text-slate-400 mb-1">What you do:</p>
              <p className="text-xs text-amber-700 font-medium">
                Watch it closely this week. It could move to READY in a few days.
                Check it during your post-market analysis.
              </p>
            </div>
          </div>

          {/* AWAY */}
          <div className="border border-slate-200 rounded-xl p-5 bg-slate-50/30">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-4 h-4 rounded-full bg-slate-400" />
              <h4 className="text-base font-bold text-slate-600">AWAY</h4>
            </div>
            <p className="text-sm text-slate-600 leading-relaxed mb-3">
              Good stock, but needs more time. Maybe it just started building a
              base, or it is still in Stage 1. Keep it on the list but do not
              watch it daily.
            </p>
            <div className="bg-white rounded-lg p-3 border border-slate-100">
              <p className="text-xs text-slate-400 mb-1">What you do:</p>
              <p className="text-xs text-slate-500 font-medium">
                Check back in a few weeks. It might take 2-4 weeks before it
                moves to NEAR.
              </p>
            </div>
          </div>
        </div>

        <Callout type="tip">
          A stock moves from AWAY to NEAR to READY as it builds its base and
          gets closer to a breakout. It is like watching a fruit ripen -- you do
          not pick it early, you wait until it is ready.
        </Callout>
      </SectionCard>

      {/* ================================================================ */}
      {/* SECTION 6 — Entry Rules */}
      {/* ================================================================ */}
      <SectionCard id="entry-rules" number={6} title="How We Buy (Entry Rules)">
        <p className="text-sm text-slate-600 leading-relaxed mb-6">
          We do not just randomly buy. There are very specific rules for when
          and how to enter a trade. Think of it like a checklist before a
          pilot takes off.
        </p>

        <StepFlow
          steps={[
            {
              label: "Identify the Trigger Level",
              detail:
                "The trigger level is the highest point of the last quiet candle in the base. Think of it as the starting line of a race. Until the stock crosses this line, we do NOT buy.",
            },
            {
              label: "Price breaks above the trigger",
              detail:
                "When the stock price goes above the trigger level during the trading day, that is our signal. Now buy 50% of your planned amount (half your shares).",
            },
            {
              label: "Wait for market close confirmation",
              detail:
                "If the stock closes ABOVE the trigger level at 3:30 PM, buy the remaining 50%. If it falls back below, do not buy the second half.",
            },
            {
              label: "Only buy in the LAST 30 minutes (3:00-3:30 PM)",
              detail:
                "This is critical. The first few hours of the trading day are wild and unpredictable. By 3:00 PM, the smart money has shown its hand. We only act in the calm final stretch.",
            },
            {
              label: "Check for earnings announcements",
              detail:
                "Never buy if the company is announcing earnings within the next 3 days. Earnings can send the stock flying up OR crashing down randomly. We do not gamble on news.",
            },
          ]}
        />

        <Callout type="warning">
          If you miss the entry at 3:00-3:30 PM, do NOT chase the stock the
          next morning. Wait. If the setup is still valid, it will give you
          another chance. Discipline is everything.
        </Callout>
      </SectionCard>

      {/* ================================================================ */}
      {/* SECTION 7 — Position Sizing */}
      {/* ================================================================ */}
      <SectionCard id="position-sizing" number={7} title="Position Sizing (How Much to Buy)">
        <p className="text-sm text-slate-600 leading-relaxed mb-4">
          This is one of the most important parts of trading. It answers the
          question: &quot;How many shares should I buy?&quot; The answer is
          based on math, not gut feeling.
        </p>
        <p className="text-sm text-slate-600 leading-relaxed mb-6">
          Let us walk through a real example step by step:
        </p>

        {/* The example walkthrough */}
        <div className="bg-slate-50 rounded-xl p-6 mb-6">
          <h4 className="text-sm font-semibold text-slate-800 mb-4">
            Real Example: Buying Shares of &quot;XYZ Ltd&quot;
          </h4>

          <div className="space-y-4">
            {/* Step 1 */}
            <div className="bg-white rounded-lg p-4 border border-slate-200">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-semibold text-slate-800">Step 1: Your account size</p>
                <span className="text-lg font-bold font-mono text-teal-600">
                  &#x20b9;5,00,000
                </span>
              </div>
              <p className="text-xs text-slate-500">This is the total money in your trading account.</p>
            </div>

            {/* Step 2 */}
            <div className="bg-white rounded-lg p-4 border border-slate-200">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-semibold text-slate-800">Step 2: Decide how much you are willing to lose on this trade</p>
                <div className="text-right">
                  <span className="text-lg font-bold font-mono text-red-600">
                    &#x20b9;2,500
                  </span>
                  <span className="text-xs text-slate-400 ml-2">
                    (0.5% of &#x20b9;5,00,000)
                  </span>
                </div>
              </div>
              <p className="text-xs text-slate-500">
                We risk 0.5% of our account per trade. This means even if this
                trade completely fails, we only lose &#x20b9;2,500 out of
                &#x20b9;5,00,000. That is nothing. We can survive many failures.
              </p>
            </div>

            {/* Step 3 */}
            <div className="bg-white rounded-lg p-4 border border-slate-200">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-semibold text-slate-800">Step 3: Stock price and TRP</p>
                <div className="text-right">
                  <p className="text-sm font-mono text-slate-700">
                    Price: <span className="font-bold">&#x20b9;601</span>
                  </p>
                  <p className="text-sm font-mono text-slate-700">
                    TRP: <span className="font-bold">3.18%</span>
                  </p>
                </div>
              </div>
              <p className="text-xs text-slate-500">
                TRP (Typical Risk Percentage) is how much the stock normally
                moves in a day. We use this to set our stop loss. A TRP of 3.18%
                means the stock typically moves about &#x20b9;19.11 per day.
              </p>
            </div>

            {/* Step 4 */}
            <div className="bg-white rounded-lg p-4 border border-slate-200">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-semibold text-slate-800">Step 4: Calculate stop loss price</p>
                <span className="text-lg font-bold font-mono text-red-600">
                  &#x20b9;581.89
                </span>
              </div>
              <div className="bg-slate-50 rounded-lg p-3 mt-2">
                <p className="text-xs text-slate-600 font-mono">
                  Stop Loss = Entry Price - (TRP% x Entry Price)
                </p>
                <p className="text-xs text-slate-600 font-mono mt-1">
                  Stop Loss = &#x20b9;601 - (3.18% x &#x20b9;601) = &#x20b9;601 - &#x20b9;19.11 = <strong>&#x20b9;581.89</strong>
                </p>
              </div>
              <p className="text-xs text-slate-500 mt-2">
                If the stock drops to &#x20b9;581.89, we sell immediately. That is our
                escape plan.
              </p>
            </div>

            {/* Step 5 */}
            <div className="bg-white rounded-lg p-4 border border-slate-200">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-semibold text-slate-800">Step 5: How many shares to buy?</p>
                <span className="text-lg font-bold font-mono text-teal-600">
                  ~131 shares
                </span>
              </div>
              <div className="bg-slate-50 rounded-lg p-3 mt-2">
                <p className="text-xs text-slate-600 font-mono">
                  Number of Shares = Max Risk / Risk per Share
                </p>
                <p className="text-xs text-slate-600 font-mono mt-1">
                  Number of Shares = &#x20b9;2,500 / &#x20b9;19.11 = <strong>~131 shares</strong>
                </p>
              </div>
              <p className="text-xs text-slate-500 mt-2">
                If we buy 131 shares at &#x20b9;601 and it drops to &#x20b9;581.89, we lose
                exactly 131 x &#x20b9;19.11 = &#x20b9;2,503 -- right at our risk limit.
              </p>
            </div>

            {/* Step 6 */}
            <div className="bg-white rounded-lg p-4 border border-teal-200 bg-teal-50/30">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-semibold text-teal-800">Step 6: Split the buy</p>
                <div className="flex items-center gap-4">
                  <div className="text-center">
                    <p className="text-xs text-slate-400">First buy</p>
                    <p className="text-sm font-bold font-mono text-teal-600">65 shares</p>
                  </div>
                  <span className="text-slate-300">+</span>
                  <div className="text-center">
                    <p className="text-xs text-slate-400">Second buy</p>
                    <p className="text-sm font-bold font-mono text-teal-600">66 shares</p>
                  </div>
                </div>
              </div>
              <p className="text-xs text-slate-500">
                Buy 65 shares first when it breaks the trigger. If it closes
                above the trigger, buy the remaining 66. This way, if the stock
                falls back, you only bought half.
              </p>
            </div>
          </div>
        </div>

        <Callout type="warning">
          Never decide how many shares to buy based on &quot;feeling.&quot;
          Always use this calculation. It is designed to protect you from
          devastating losses.
        </Callout>
      </SectionCard>

      {/* ================================================================ */}
      {/* SECTION 8 — Stop Loss */}
      {/* ================================================================ */}
      <SectionCard id="stop-loss" number={8} title="Stop Loss (Protecting Yourself)">
        <p className="text-sm text-slate-600 leading-relaxed mb-6">
          A stop loss is your escape plan. Before you ever buy a single share,
          you decide: &quot;If the stock drops to THIS price, I sell immediately,
          no questions asked.&quot; It is like a seatbelt in a car -- you hope
          you never need it, but you always wear it.
        </p>

        <div className="bg-slate-50 rounded-xl p-5 mb-6">
          <h4 className="text-sm font-semibold text-slate-800 mb-3">How to Calculate Your Stop Loss:</h4>
          <div className="bg-white rounded-lg p-4 border border-slate-200">
            <p className="text-sm font-mono text-slate-700 text-center">
              Stop Loss Price = Entry Price - TRP Amount
            </p>
            <p className="text-sm font-mono text-slate-500 text-center mt-2">
              Example: &#x20b9;601 - &#x20b9;19.11 = <span className="font-bold text-red-600">&#x20b9;581.89</span>
            </p>
          </div>
        </div>

        {/* The 3 rules */}
        <h4 className="text-sm font-semibold text-slate-800 mb-3">The 3 Golden Rules of Stop Loss:</h4>
        <div className="space-y-3 mb-6">
          <div className="flex items-start gap-3 border border-amber-200 bg-amber-50/30 rounded-xl p-4">
            <span className="flex-shrink-0 w-8 h-8 bg-amber-500 text-white rounded-lg flex items-center justify-center text-sm font-bold">1</span>
            <div>
              <p className="text-sm font-semibold text-slate-800">Wait 10 minutes after market opens</p>
              <p className="text-xs text-slate-600 mt-0.5">
                The first 10 minutes (9:15-9:25 AM) are chaos. Stocks bounce
                wildly as overnight orders pour in. Your stock might dip below
                the stop loss and bounce right back. Wait for the dust to
                settle before checking if your stop loss has been hit.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3 border border-red-200 bg-red-50/30 rounded-xl p-4">
            <span className="flex-shrink-0 w-8 h-8 bg-red-600 text-white rounded-lg flex items-center justify-center text-sm font-bold">2</span>
            <div>
              <p className="text-sm font-semibold text-slate-800">NEVER move your stop loss DOWN</p>
              <p className="text-xs text-slate-600 mt-0.5">
                If the stock is dropping toward your stop loss, you might think:
                &quot;Let me give it more room, maybe it will bounce.&quot; DO
                NOT DO THIS. Moving your stop loss down means you are now
                risking more money than planned. This is how small losses become
                devastating losses.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3 border border-emerald-200 bg-emerald-50/30 rounded-xl p-4">
            <span className="flex-shrink-0 w-8 h-8 bg-emerald-600 text-white rounded-lg flex items-center justify-center text-sm font-bold">3</span>
            <div>
              <p className="text-sm font-semibold text-slate-800">You CAN move your stop loss UP</p>
              <p className="text-xs text-slate-600 mt-0.5">
                As the stock goes in your favour, move your stop loss up to lock
                in profits. If you bought at &#x20b9;601 and it is now at &#x20b9;640,
                move your stop loss from &#x20b9;581.89 up to &#x20b9;620. Now even if the
                stock drops, you still make a profit.
              </p>
            </div>
          </div>
        </div>

        <Callout type="danger">
          The number one reason traders blow up their accounts is not having a
          stop loss, or not following it. ALWAYS have a stop loss. ALWAYS
          follow it. No exceptions.
        </Callout>
      </SectionCard>

      {/* ================================================================ */}
      {/* SECTION 9 — Taking Profits */}
      {/* ================================================================ */}
      <SectionCard id="taking-profits" number={9} title="Taking Profits (The Exit Framework)">
        <p className="text-sm text-slate-600 leading-relaxed mb-4">
          Knowing when to sell is just as important as knowing when to buy. We
          use a &quot;ladder&quot; approach -- selling in pieces as the stock
          goes higher, like climbing a staircase and collecting money at each
          step.
        </p>
        <p className="text-sm text-slate-600 leading-relaxed mb-6">
          We measure our targets using &quot;R&quot; -- which means multiples of
          risk. If you risked &#x20b9;19.11 per share (your TRP), then 2R =
          &#x20b9;38.22 profit, 4R = &#x20b9;76.44, and so on.
        </p>

        {/* Exit ladder visual */}
        <div className="bg-slate-50 rounded-xl p-6 mb-6">
          <h4 className="text-xs text-slate-400 font-semibold uppercase tracking-wider mb-4 text-center">
            The Profit-Taking Ladder (Real Numbers: Entry &#x20b9;601, Risk &#x20b9;19.11/share)
          </h4>

          <div className="space-y-3">
            {/* Extreme Extension */}
            <div className="flex items-center gap-3">
              <div className="w-28 md:w-40 text-right">
                <p className="text-xs font-bold text-emerald-700">12R: Extreme</p>
                <p className="text-xs font-mono text-slate-500">&#x20b9;830.32</p>
              </div>
              <div className="flex-1 relative">
                <div className="h-8 bg-emerald-600 rounded-lg flex items-center" style={{ width: "100%" }}>
                  <span className="text-xs text-white font-bold px-3">Sell 80% of remaining</span>
                </div>
              </div>
              <span className="w-14 text-xs font-mono text-emerald-600 font-bold">+&#x20b9;229</span>
            </div>

            {/* Great Extension */}
            <div className="flex items-center gap-3">
              <div className="w-28 md:w-40 text-right">
                <p className="text-xs font-bold text-emerald-600">8R: Great</p>
                <p className="text-xs font-mono text-slate-500">&#x20b9;753.88</p>
              </div>
              <div className="flex-1 relative">
                <div className="h-8 bg-emerald-500 rounded-lg flex items-center" style={{ width: "75%" }}>
                  <span className="text-xs text-white font-bold px-3">Sell 40%</span>
                </div>
              </div>
              <span className="w-14 text-xs font-mono text-emerald-600 font-bold">+&#x20b9;153</span>
            </div>

            {/* Normal Extension */}
            <div className="flex items-center gap-3">
              <div className="w-28 md:w-40 text-right">
                <p className="text-xs font-bold text-teal-600">4R: Normal</p>
                <p className="text-xs font-mono text-slate-500">&#x20b9;677.44</p>
              </div>
              <div className="flex-1 relative">
                <div className="h-8 bg-teal-500 rounded-lg flex items-center" style={{ width: "50%" }}>
                  <span className="text-xs text-white font-bold px-3">Sell 20%</span>
                </div>
              </div>
              <span className="w-14 text-xs font-mono text-teal-600 font-bold">+&#x20b9;76</span>
            </div>

            {/* 2R Target */}
            <div className="flex items-center gap-3">
              <div className="w-28 md:w-40 text-right">
                <p className="text-xs font-bold text-blue-600">2R: First Target</p>
                <p className="text-xs font-mono text-slate-500">&#x20b9;639.22</p>
              </div>
              <div className="flex-1 relative">
                <div className="h-8 bg-blue-500 rounded-lg flex items-center" style={{ width: "30%" }}>
                  <span className="text-xs text-white font-bold px-3">Sell 20%</span>
                </div>
              </div>
              <span className="w-14 text-xs font-mono text-blue-600 font-bold">+&#x20b9;38</span>
            </div>

            {/* Entry */}
            <div className="flex items-center gap-3">
              <div className="w-28 md:w-40 text-right">
                <p className="text-xs font-bold text-slate-600">Entry</p>
                <p className="text-xs font-mono text-slate-500">&#x20b9;601.00</p>
              </div>
              <div className="flex-1 border-t-2 border-dashed border-slate-400" />
              <span className="w-14 text-xs font-mono text-slate-500">&#x20b9;0</span>
            </div>

            {/* Stop Loss */}
            <div className="flex items-center gap-3">
              <div className="w-28 md:w-40 text-right">
                <p className="text-xs font-bold text-red-600">Stop Loss</p>
                <p className="text-xs font-mono text-slate-500">&#x20b9;581.89</p>
              </div>
              <div className="flex-1 border-t-2 border-dashed border-red-400" />
              <span className="w-14 text-xs font-mono text-red-600 font-bold">-&#x20b9;19</span>
            </div>
          </div>
        </div>

        <Callout type="tip">
          You do NOT have to sell at every level. If the stock is rocketing up
          with strong momentum, you can hold longer. But the ladder gives you a
          plan -- and having a plan is better than guessing.
        </Callout>
      </SectionCard>

      {/* ================================================================ */}
      {/* SECTION 10 — Risk Management */}
      {/* ================================================================ */}
      <SectionCard id="risk-management" number={10} title="Risk Management (The Safety Rules)">
        <p className="text-sm text-slate-600 leading-relaxed mb-6">
          Risk management is the most boring-sounding but most important part of
          trading. Professionals do not focus on making money -- they focus on not
          losing it. The money follows naturally.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {/* Rule 1 */}
          <div className="bg-white rounded-xl border-2 border-red-200 p-5 text-center">
            <div className="w-12 h-12 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-3">
              <span className="text-xl font-bold text-red-600 font-mono">1%</span>
            </div>
            <p className="text-sm font-semibold text-slate-800 mb-1">Max Risk Per Trade</p>
            <p className="text-xs text-slate-500">
              Never risk more than 1% of your total account on a single trade.
              Most of the time we risk 0.5%.
            </p>
            <div className="bg-red-50 rounded-lg p-2 mt-3">
              <p className="text-xs text-red-700">
                Account: &#x20b9;5,00,000
              </p>
              <p className="text-xs font-bold text-red-700">
                Max risk: &#x20b9;5,000
              </p>
            </div>
          </div>

          {/* Rule 2 */}
          <div className="bg-white rounded-xl border-2 border-amber-200 p-5 text-center">
            <div className="w-12 h-12 rounded-full bg-amber-50 flex items-center justify-center mx-auto mb-3">
              <span className="text-xl font-bold text-amber-600 font-mono">10%</span>
            </div>
            <p className="text-sm font-semibold text-slate-800 mb-1">Max Total Risk</p>
            <p className="text-xs text-slate-500">
              Never have more than 10% of your account at risk at any one time
              across ALL open trades combined.
            </p>
            <div className="bg-amber-50 rounded-lg p-2 mt-3">
              <p className="text-xs text-amber-700">
                Account: &#x20b9;5,00,000
              </p>
              <p className="text-xs font-bold text-amber-700">
                Max total risk: &#x20b9;50,000
              </p>
            </div>
          </div>

          {/* Rule 3 */}
          <div className="bg-white rounded-xl border-2 border-teal-200 p-5 text-center">
            <div className="w-12 h-12 rounded-full bg-teal-50 flex items-center justify-center mx-auto mb-3">
              <span className="text-lg font-bold text-teal-600">Adjust</span>
            </div>
            <p className="text-sm font-semibold text-slate-800 mb-1">Adapt to Market</p>
            <p className="text-xs text-slate-500">
              In weak markets, risk less (0.2%). In normal markets, risk the
              standard (0.5%). In strong markets, risk more (0.8%).
            </p>
            <div className="bg-teal-50 rounded-lg p-2 mt-3 space-y-0.5">
              <p className="text-xs text-red-600">Weak: 0.2% = &#x20b9;1,000</p>
              <p className="text-xs text-amber-600">Normal: 0.5% = &#x20b9;2,500</p>
              <p className="text-xs text-emerald-600">Strong: 0.8% = &#x20b9;4,000</p>
            </div>
          </div>
        </div>

        <Callout type="tip">
          Think of it this way: if you risk 0.5% per trade and have a losing
          streak of 10 trades in a row (which is rare), you only lose 5% of
          your account. You can recover from that. But if you risk 10% per
          trade, 5 losses in a row and half your account is gone.
        </Callout>
      </SectionCard>

      {/* ================================================================ */}
      {/* SECTION 11 — Daily Routine */}
      {/* ================================================================ */}
      <SectionCard id="daily-routine" number={11} title="The Daily Routine">
        <p className="text-sm text-slate-600 leading-relaxed mb-6">
          One of the best things about swing trading is that it does NOT require
          you to stare at screens all day. The entire system runs on a simple
          daily routine that takes about 2 hours total.
        </p>

        {/* Timeline visual */}
        <div className="space-y-0 mb-6">
          {/* Morning */}
          <div className="flex gap-4">
            <div className="flex flex-col items-center">
              <div className="w-10 h-10 rounded-full bg-amber-100 border-2 border-amber-400 flex items-center justify-center flex-shrink-0">
                <span className="text-[10px] font-bold text-amber-700">AM</span>
              </div>
              <div className="w-0.5 flex-1 bg-slate-200" />
            </div>
            <div className="pb-6 flex-1">
              <div className="bg-white rounded-xl border border-slate-200 p-4">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-bold text-slate-800">9:15 AM -- Market Opens</p>
                  <span className="text-[10px] bg-amber-100 text-amber-700 rounded-full px-2 py-0.5 font-medium">15 minutes</span>
                </div>
                <ul className="text-xs text-slate-600 space-y-1 list-disc list-inside">
                  <li>Wait 10 minutes for the opening chaos to settle</li>
                  <li>Check your open trades -- is anything near the stop loss?</li>
                  <li>Set stop loss alerts if not already set</li>
                  <li>That is it. Close the app. Go about your day.</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Afternoon */}
          <div className="flex gap-4">
            <div className="flex flex-col items-center">
              <div className="w-10 h-10 rounded-full bg-teal-100 border-2 border-teal-400 flex items-center justify-center flex-shrink-0">
                <span className="text-[10px] font-bold text-teal-700">3PM</span>
              </div>
              <div className="w-0.5 flex-1 bg-slate-200" />
            </div>
            <div className="pb-6 flex-1">
              <div className="bg-white rounded-xl border border-teal-200 p-4 bg-teal-50/20">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-bold text-teal-800">3:00 PM -- Last 30 Minutes</p>
                  <span className="text-[10px] bg-teal-100 text-teal-700 rounded-full px-2 py-0.5 font-medium">30 minutes</span>
                </div>
                <ul className="text-xs text-slate-600 space-y-1 list-disc list-inside">
                  <li>Check your READY stocks -- did any break the trigger today?</li>
                  <li>If yes, use the calculator to figure out position size</li>
                  <li>Place the buy order between 3:00-3:30 PM</li>
                  <li>If nothing triggered, do nothing. Patience pays.</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Post-market */}
          <div className="flex gap-4">
            <div className="flex flex-col items-center">
              <div className="w-10 h-10 rounded-full bg-blue-100 border-2 border-blue-400 flex items-center justify-center flex-shrink-0">
                <span className="text-[10px] font-bold text-blue-700">EVE</span>
              </div>
              <div className="w-0.5 flex-1 bg-slate-200" />
            </div>
            <div className="pb-6 flex-1">
              <div className="bg-white rounded-xl border border-slate-200 p-4">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-bold text-slate-800">3:30 PM -- Post-Market Analysis</p>
                  <span className="text-[10px] bg-blue-100 text-blue-700 rounded-full px-2 py-0.5 font-medium">1 hour</span>
                </div>
                <ul className="text-xs text-slate-600 space-y-1 list-disc list-inside">
                  <li>Run PPC, NPC, and Contraction scans</li>
                  <li>Review the scan results -- any new stocks to add to watchlist?</li>
                  <li>Update your watchlist (move stocks between AWAY/NEAR/READY)</li>
                  <li>Log the day&apos;s market stance (Strong / Moderate / Weak)</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Weekend */}
          <div className="flex gap-4">
            <div className="flex flex-col items-center">
              <div className="w-10 h-10 rounded-full bg-slate-100 border-2 border-slate-300 flex items-center justify-center flex-shrink-0">
                <span className="text-[10px] font-bold text-slate-600">SAT</span>
              </div>
            </div>
            <div className="flex-1">
              <div className="bg-white rounded-xl border border-slate-200 p-4">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-bold text-slate-800">Weekend -- Weekly Review</p>
                  <span className="text-[10px] bg-slate-100 text-slate-600 rounded-full px-2 py-0.5 font-medium">2 hours</span>
                </div>
                <ul className="text-xs text-slate-600 space-y-1 list-disc list-inside">
                  <li>Fill out your weekly trading journal (see next section)</li>
                  <li>Review all closed trades -- what went right, what went wrong?</li>
                  <li>Do deeper chart analysis on NEAR and AWAY stocks</li>
                  <li>Plan for the coming week</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        <Callout type="tip">
          Total daily time: about 1 hour 45 minutes. Most of your day is free.
          Swing trading is NOT about watching screens all day. It is about
          following a process at specific times.
        </Callout>
      </SectionCard>

      {/* ================================================================ */}
      {/* SECTION 12 — Weekly Journal */}
      {/* ================================================================ */}
      <SectionCard id="weekly-journal" number={12} title="The Weekly Journal">
        <p className="text-sm text-slate-600 leading-relaxed mb-6">
          Every weekend, you sit down and honestly answer questions about your
          trading week. This is not about beating yourself up -- it is about
          getting better. The best traders are the ones who learn from every
          trade, good or bad.
        </p>

        {/* Grave Mistakes */}
        <div className="bg-red-50 border border-red-200 rounded-xl p-5 mb-6">
          <h4 className="text-sm font-bold text-red-800 mb-3">
            The &quot;Grave Mistakes&quot; Checklist
          </h4>
          <p className="text-xs text-red-700 mb-3">
            These are 5 things you must NEVER do. Each week, check honestly. If
            any answer is &quot;Yes&quot;, it is a serious problem that needs
            fixing.
          </p>
          <div className="space-y-2">
            {[
              "Did I trade without a stop loss?",
              "Did I move my stop loss DOWN (gave a losing trade more room)?",
              "Did I buy a stock that was NOT in Stage 2?",
              "Did I risk more than 1% of my account on a single trade?",
              "Did I buy on impulse without checking the setup rules?",
            ].map((mistake, index) => (
              <div
                key={index}
                className="flex items-center gap-3 bg-white rounded-lg p-3 border border-red-100"
              >
                <div className="w-5 h-5 rounded border-2 border-red-300 flex-shrink-0" />
                <p className="text-sm text-slate-700">{mistake}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Performance tracking */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <h4 className="text-sm font-semibold text-slate-800 mb-3">
              Key Numbers to Track
            </h4>
            <div className="space-y-3">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-slate-500">Win Rate (target: above 40%)</span>
                  <span className="text-xs font-mono font-bold text-teal-600">&gt;40%</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2">
                  <div className="bg-teal-500 h-2 rounded-full" style={{ width: "40%" }} />
                </div>
                <p className="text-[10px] text-slate-400 mt-1">
                  You only need to win 4 out of 10 trades to be profitable
                </p>
              </div>
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-slate-500">Reward-to-Risk Ratio (target: above 2)</span>
                  <span className="text-xs font-mono font-bold text-teal-600">&gt;2.0</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2">
                  <div className="bg-emerald-500 h-2 rounded-full" style={{ width: "66%" }} />
                </div>
                <p className="text-[10px] text-slate-400 mt-1">
                  Your average winner should be at least 2x your average loser
                </p>
              </div>
            </div>
          </div>

          {/* The math */}
          <div className="bg-teal-50 border border-teal-200 rounded-xl p-5">
            <h4 className="text-sm font-semibold text-teal-800 mb-3">
              The Surprising Math of Trading
            </h4>
            <p className="text-sm text-teal-700 leading-relaxed mb-3">
              Even if you lose 60% of your trades, you can still make money!
              Here is how:
            </p>
            <div className="bg-white rounded-lg p-4 border border-teal-100">
              <div className="space-y-2 text-xs font-mono text-slate-700">
                <p>10 trades total, risking &#x20b9;2,500 each:</p>
                <p className="text-red-600">
                  6 losses x &#x20b9;2,500 = -&#x20b9;15,000
                </p>
                <p className="text-emerald-600">
                  4 wins x &#x20b9;5,000 (2R avg) = +&#x20b9;20,000
                </p>
                <div className="border-t border-slate-200 pt-2 mt-2">
                  <p className="text-base font-bold text-emerald-700">
                    Net profit: +&#x20b9;5,000
                  </p>
                  <p className="text-slate-500 font-sans text-[10px] mt-1">
                    Lost 6 out of 10 trades but still made money. That is the
                    power of good risk management.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <Callout type="tip">
          The journal is not about perfection. It is about progress. Every
          weekend review makes you 1% better. After a year, that is a
          completely different trader looking back at you in the mirror.
        </Callout>
      </SectionCard>

      {/* ================================================================ */}
      {/* Final Summary Card */}
      {/* ================================================================ */}
      <div className="bg-teal-50 border border-teal-200 rounded-xl p-6">
        <h3 className="text-base font-bold text-teal-800 mb-3">
          The Champion Trader Methodology in One Sentence
        </h3>
        <p className="text-sm text-teal-700 leading-relaxed">
          Find stocks in Stage 2 that are building tight bases, buy them when
          they break out with a strict position size, protect every trade with a
          stop loss, take profits in steps, never risk more than you can afford,
          and review your performance every week.
        </p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
          <div className="bg-white rounded-lg p-3 border border-teal-100 text-center">
            <p className="text-lg font-bold text-teal-600">Stage 2</p>
            <p className="text-[10px] text-slate-500">Only buy here</p>
          </div>
          <div className="bg-white rounded-lg p-3 border border-teal-100 text-center">
            <p className="text-lg font-bold text-teal-600">0.5%</p>
            <p className="text-[10px] text-slate-500">Risk per trade</p>
          </div>
          <div className="bg-white rounded-lg p-3 border border-teal-100 text-center">
            <p className="text-lg font-bold text-teal-600">3:00 PM</p>
            <p className="text-[10px] text-slate-500">Buy in last 30 min</p>
          </div>
          <div className="bg-white rounded-lg p-3 border border-teal-100 text-center">
            <p className="text-lg font-bold text-teal-600">&gt;2R</p>
            <p className="text-[10px] text-slate-500">Winners beat losers</p>
          </div>
        </div>
      </div>

      {/* Spacer at bottom for comfortable scrolling */}
      <div className="h-8" />
    </div>
  );
}
