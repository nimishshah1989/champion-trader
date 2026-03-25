"use client";

import Link from "next/link";

// ---------------------------------------------------------------------------
// Reusable Section Components
// ---------------------------------------------------------------------------

export function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-base font-semibold text-slate-800">{children}</h2>
  );
}

function SimpleCard({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`bg-white rounded-xl border border-slate-200 p-6 ${className}`}
    >
      {children}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 1. The Big Picture — What is this tool?
// ---------------------------------------------------------------------------

export function WhatIsThisTool() {
  return (
    <SimpleCard>
      <h3 className="text-lg font-semibold text-slate-800 mb-3">
        What does this tool do?
      </h3>
      <p className="text-sm text-slate-700 leading-relaxed mb-4">
        Think of this as your{" "}
        <span className="font-semibold text-teal-600">
          personal stock market assistant
        </span>
        . Every day, it scans hundreds of stocks on the Indian stock market
        (NSE), finds the ones that look promising, and presents them to you
        as simple &ldquo;cards&rdquo; — like a waiter bringing you a menu.
      </p>
      <p className="text-sm text-slate-700 leading-relaxed mb-4">
        <span className="font-semibold">You make every decision.</span> The
        tool finds opportunities. You decide whether to act on them or skip
        them. It never buys or sells anything without you clicking a button.
      </p>
      <p className="text-sm text-slate-700 leading-relaxed">
        Over time, it also learns what worked and what didn&rsquo;t, and
        adjusts its scanning criteria to get better — like a chef who tweaks
        a recipe based on customer feedback.
      </p>
    </SimpleCard>
  );
}

// ---------------------------------------------------------------------------
// 2. Your Daily Routine — Step by Step
// ---------------------------------------------------------------------------

interface DailyStep {
  emoji: string;
  time: string;
  title: string;
  detail: string;
  page: string;
  href: string;
}

export function DailyRoutine() {
  const steps: DailyStep[] = [
    {
      emoji: "☀️",
      time: "Morning (before 9:15 AM)",
      title: "Open the Intelligence Dashboard",
      detail:
        "You'll see a quick snapshot: what kind of market day to expect, your current risk level, and a short daily summary written by the system overnight. Think of it like reading a one-paragraph newspaper before you start your day.",
      page: "Intelligence",
      href: "/intelligence",
    },
    {
      emoji: "📋",
      time: "Morning",
      title: "Review the Stock Suggestions",
      detail:
        "The system shows you up to 3 stock \"setup cards\" — each one is a stock that passed all the filters. Each card shows the stock name, a confidence score (0–100), the suggested buy price, and where to place your safety net (stop-loss). Read the one-line reason, then click Approve or Skip.",
      page: "Intelligence",
      href: "/intelligence",
    },
    {
      emoji: "✅",
      time: "During market hours",
      title: "Track Your Trades",
      detail:
        "If you approved a stock and it triggered your buy price, it shows up in your Trades page. The system watches your positions and automatically alerts you if a stop-loss level is hit. You handle the actual buying and selling through your broker (Zerodha, Dhan, etc.).",
      page: "Trades",
      href: "/trades",
    },
    {
      emoji: "🌙",
      time: "After market closes (automatic)",
      title: "The System Learns Overnight",
      detail:
        "After the market closes, the system runs a series of background tasks — it checks what kind of market we had today, writes a brief summary, and runs experiments to improve its stock-picking criteria. You don't need to do anything. Just check the results next morning.",
      page: "Optimize",
      href: "/intelligence/optimize",
    },
    {
      emoji: "📊",
      time: "Once a week",
      title: "Check How You're Doing",
      detail:
        "The Shadow Portfolio page answers one question: \"Am I picking better stocks than the machine would on its own?\" It tracks every suggestion — both the ones you approved AND the ones you skipped — so you can compare. If you're adding value, great. If not, you might want to trust the system more.",
      page: "Shadow",
      href: "/intelligence/shadow",
    },
  ];

  return (
    <SimpleCard>
      <h3 className="text-lg font-semibold text-slate-800 mb-1">
        Your Daily Routine
      </h3>
      <p className="text-xs text-slate-400 mb-5">
        Here&rsquo;s what a typical day looks like using this tool
      </p>
      <div className="space-y-6">
        {steps.map((step, i) => (
          <div key={i} className="flex gap-4">
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-teal-50 border border-teal-200 flex items-center justify-center text-lg">
              {step.emoji}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <p className="text-sm font-semibold text-slate-800">
                  {step.title}
                </p>
                <span className="text-[10px] text-slate-400 font-medium">
                  {step.time}
                </span>
              </div>
              <p className="text-sm text-slate-600 leading-relaxed">
                {step.detail}
              </p>
              <Link
                href={step.href}
                className="text-xs text-teal-600 hover:text-teal-700 font-medium mt-1 inline-block"
              >
                Go to {step.page} →
              </Link>
            </div>
          </div>
        ))}
      </div>
    </SimpleCard>
  );
}

// ---------------------------------------------------------------------------
// 3. Each Page Explained — In Plain Language
// ---------------------------------------------------------------------------

function PageExplainedCard({
  title,
  href,
  oneLiner,
  children,
}: {
  title: string;
  href: string;
  oneLiner: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 hover:border-teal-200 transition-colors">
      <Link
        href={href}
        className="text-base font-semibold text-teal-600 hover:text-teal-700"
      >
        {title} →
      </Link>
      <p className="text-sm text-slate-500 mt-1 mb-3">{oneLiner}</p>
      <div className="text-sm text-slate-700 leading-relaxed space-y-2">
        {children}
      </div>
    </div>
  );
}

export function PagesExplained() {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <PageExplainedCard
        title="Intelligence Dashboard"
        href="/intelligence"
        oneLiner="Your morning briefing — check this first"
      >
        <p>
          This is your home base. It shows 4 things at a glance:
        </p>
        <ul className="list-disc list-inside text-sm text-slate-600 space-y-1 ml-1">
          <li>
            <strong>Market Mood</strong> — Is the overall market trending up,
            going sideways, volatile, or falling? This affects which stocks
            the system recommends.
          </li>
          <li>
            <strong>Risk Level</strong> — How much of your money is currently
            at risk in open trades. Shown as a percentage.
          </li>
          <li>
            <strong>Daily Summary</strong> — A short paragraph written by the
            system summarizing what happened and what to watch for.
          </li>
          <li>
            <strong>Stock Picks</strong> — Up to 3 stocks the system thinks
            are worth buying today. You approve or skip each one.
          </li>
        </ul>
      </PageExplainedCard>

      <PageExplainedCard
        title="Optimize"
        href="/intelligence/optimize"
        oneLiner="How the system improves itself over time"
      >
        <p>
          Imagine you have a recipe for making chai. This page shows you a
          kitchen assistant who experiments with the recipe every night —
          trying slightly more ginger, a bit less sugar — and tests each
          version to see if it tastes better.
        </p>
        <p>
          That&rsquo;s what AutoOptimize does with stock-picking rules. It
          tweaks one thing at a time, runs it against past market data, and
          keeps changes that improve results.
        </p>
        <p className="text-xs text-slate-400 mt-1">
          You can start it manually or let it run automatically at 6 PM on
          weekdays. Check results the next morning.
        </p>
      </PageExplainedCard>

      <PageExplainedCard
        title="Shadow Portfolio"
        href="/intelligence/shadow"
        oneLiner="Are you picking better stocks than the machine?"
      >
        <p>
          Every time the system suggests a stock, it secretly tracks what
          would have happened if you had bought it — regardless of whether
          you actually approved it or skipped it.
        </p>
        <p>
          This page shows a simple comparison:
        </p>
        <ul className="list-disc list-inside text-sm text-slate-600 space-y-1 ml-1">
          <li>
            <strong>Machine&rsquo;s results</strong> (all suggestions,
            no filtering)
          </li>
          <li>
            <strong>Your results</strong> (only the ones you approved)
          </li>
          <li>
            <strong>Human Alpha</strong> — Are you adding value? A positive
            number means yes.
          </li>
        </ul>
      </PageExplainedCard>

      <PageExplainedCard
        title="Attribution"
        href="/intelligence/attribution"
        oneLiner="Which types of signals work best in which market conditions?"
      >
        <p>
          This is a scorecard. The system generates different types of stock
          signals (strong momentum, breakouts, quiet accumulation). This
          page shows you which signal types are winning and which are losing
          — broken down by market conditions.
        </p>
        <p>
          <strong>Example:</strong> You might discover that breakout signals
          do well in trending markets but poorly in sideways markets. This
          helps you decide which suggestions to trust.
        </p>
        <p className="text-xs text-slate-400 mt-1">
          Check this once a month — it needs enough data to show meaningful
          patterns.
        </p>
      </PageExplainedCard>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 4. Behind the Scenes — The 7 Timers (demystified)
// ---------------------------------------------------------------------------

export function BehindTheScenes() {
  const timers = [
    {
      name: "Safety Monitor",
      simple: "Checks if any of your stocks have fallen to the safety-net (stop-loss) level",
      when: "Every 10 minutes during market hours",
      icon: "🛡️",
    },
    {
      name: "Trade Reviewer",
      simple: "Looks at recently closed trades and records whether they were wins or losses",
      when: "Every 30 minutes during market hours",
      icon: "📝",
    },
    {
      name: "Market Mood Check",
      simple: "Determines if the overall market is trending up, sideways, volatile, or falling",
      when: "4:45 PM on weekdays",
      icon: "🌡️",
    },
    {
      name: "Daily Summary Writer",
      simple: "Writes a brief paragraph summarizing the day and what to watch for tomorrow",
      when: "5:00 PM on weekdays",
      icon: "📰",
    },
    {
      name: "Market Data Saver",
      simple: "Saves today's market data (index levels, big movers) so the system remembers it",
      when: "5:30 PM on weekdays",
      icon: "💾",
    },
    {
      name: "Recipe Improver",
      simple: "Runs overnight experiments to improve the stock-picking rules (tests one change at a time)",
      when: "6:00 PM on weekdays (runs overnight)",
      icon: "🔬",
    },
    {
      name: "Shadow Tracker",
      simple: "Updates the paper-trade portfolio that tracks ALL suggestions (approved + skipped)",
      when: "Every 30 minutes during market hours",
      icon: "👤",
    },
  ];

  return (
    <SimpleCard>
      <h3 className="text-lg font-semibold text-slate-800 mb-1">
        Behind the Scenes — 7 Automated Timers
      </h3>
      <p className="text-sm text-slate-500 mb-2">
        These are <strong>not</strong> AI robots making decisions. They are
        simple scheduled tasks — like alarm clocks that run a specific job
        when the time comes. If the server is off, they don&rsquo;t run.
      </p>
      <p className="text-xs text-slate-400 mb-5">
        Technical detail: They use a Python library called APScheduler — the
        same thing that makes cron jobs work on a server. Each &ldquo;agent&rdquo; is just
        a Python function that runs on a timer.
      </p>

      <div className="space-y-3">
        {timers.map((t) => (
          <div
            key={t.name}
            className="flex items-start gap-3 border-b border-slate-100 pb-3 last:border-0 last:pb-0"
          >
            <span className="text-xl flex-shrink-0 mt-0.5">{t.icon}</span>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <p className="text-sm font-semibold text-slate-800">
                  {t.name}
                </p>
                <span className="text-[10px] font-mono text-teal-600 bg-teal-50 border border-teal-200 rounded-full px-2 py-0.5">
                  {t.when}
                </span>
              </div>
              <p className="text-sm text-slate-600 mt-0.5">{t.simple}</p>
            </div>
          </div>
        ))}
      </div>
    </SimpleCard>
  );
}

