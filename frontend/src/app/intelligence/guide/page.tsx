"use client";

import Link from "next/link";

// ---------------------------------------------------------------------------
// Reusable Section Components
// ---------------------------------------------------------------------------

function SectionHeading({ children }: { children: React.ReactNode }) {
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

function WhatIsThisTool() {
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

function DailyRoutine() {
  const steps = [
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

function PagesExplained() {
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

function BehindTheScenes() {
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

// ---------------------------------------------------------------------------
// 5. Jargon Buster — Key Terms in Plain Language
// ---------------------------------------------------------------------------

function JargonBuster() {
  const terms = [
    {
      term: "Stop-Loss (SL)",
      simple:
        "A safety net. If a stock falls to this price, you sell it to limit your loss. Like a seatbelt — you hope you never need it, but it protects you when things go wrong.",
    },
    {
      term: "Market Regime / Market Mood",
      simple:
        "Is the market happy (trending up), moody (volatile), bored (sideways), or sad (falling)? The system detects this automatically and adjusts its behavior — just like you'd carry an umbrella on a cloudy day.",
    },
    {
      term: "R-Multiple",
      simple:
        "A simple way to measure profit relative to risk. If you risked ₹100 and made ₹200, that's a 2R trade. If you risked ₹100 and lost ₹100, that's -1R. Higher R = better trade.",
    },
    {
      term: "Win Rate",
      simple:
        "Out of all your trades, what percentage were winners? If you made 10 trades and 6 were profitable, your win rate is 60%.",
    },
    {
      term: "RPT (Risk Per Trade)",
      simple:
        "How much of your total money you're willing to risk on a single trade. Default is 0.5% — so if you have ₹10,00,000, you'd risk ₹5,000 per trade. Small enough that one bad trade won't hurt you.",
    },
    {
      term: "Human Alpha",
      simple:
        "Are YOUR decisions adding value? If the machine suggests 10 stocks and you pick the 5 best ones, you have positive alpha. If you consistently skip the winners, your alpha is negative.",
    },
    {
      term: "Composite Score",
      simple:
        "A single number (like a school exam score) that measures how well the stock-picking rules are performing. The overnight optimizer tries to make this number go up.",
    },
    {
      term: "PPC / NPC / Contraction",
      simple:
        "Three types of stock patterns the system looks for. PPC (Positive Price Candle) means a strong green day with high volume. NPC is the opposite. Contraction means the stock is getting very quiet — often a sign it's about to make a big move.",
    },
    {
      term: "Parameter Banks",
      simple:
        "Different sets of rules for different market moods. Like how you'd drive differently on a highway vs a village road — the system has different settings for trending vs volatile vs quiet markets.",
    },
    {
      term: "Expectancy",
      simple:
        "If you repeat this strategy many times, how much profit can you expect per trade on average? A positive expectancy means the system has an edge. Like a casino — they have positive expectancy on every game.",
    },
  ];

  return (
    <SimpleCard>
      <h3 className="text-lg font-semibold text-slate-800 mb-1">
        Jargon Buster
      </h3>
      <p className="text-xs text-slate-400 mb-5">
        Every technical term explained in everyday language
      </p>
      <div className="space-y-4">
        {terms.map((t) => (
          <div
            key={t.term}
            className="border-b border-slate-100 pb-4 last:border-0 last:pb-0"
          >
            <p className="text-sm font-semibold text-slate-800">{t.term}</p>
            <p className="text-sm text-slate-600 mt-1 leading-relaxed">
              {t.simple}
            </p>
          </div>
        ))}
      </div>
    </SimpleCard>
  );
}

// ---------------------------------------------------------------------------
// 6. FAQ — Common Questions
// ---------------------------------------------------------------------------

function FAQ() {
  const questions = [
    {
      q: "Will this tool buy or sell stocks on my behalf?",
      a: "No. The tool ONLY suggests stocks. You make every buy/sell decision yourself through your own broker (Zerodha, Dhan, Groww, etc.). The only exception is the Safety Monitor which will alert you if a stop-loss is hit — but even then, you execute the trade.",
    },
    {
      q: "What if I don't check it every day?",
      a: "Nothing bad happens. The system runs in the background, but it doesn't take action without you. If you skip a day, you just miss that day's suggestions. Your existing positions are still monitored by the Safety Monitor.",
    },
    {
      q: "How much money do I need to start?",
      a: "The tool works with any amount — the default is ₹1,00,000 but you can set it to whatever your actual trading capital is. It automatically calculates position sizes based on your capital so you never risk too much on one trade.",
    },
    {
      q: "What are these 'agents' I keep hearing about?",
      a: "They're just automated timers — like setting an alarm. At specific times during the day, the system runs a task (check risk, classify market, write summary). They're NOT AI robots making decisions. Think of them as scheduled chores the system does automatically.",
    },
    {
      q: "How does the system 'learn'?",
      a: "After each trade closes (win or loss), the system records what happened. Over time, it can see patterns — like 'breakout signals in volatile markets tend to fail'. The overnight optimizer then adjusts the stock-picking criteria based on these patterns, running hundreds of experiments against past data.",
    },
    {
      q: "Is my money safe?",
      a: "This tool has NO access to your bank account or broker account. It cannot move money, buy stocks, or sell stocks. It is a suggestion and tracking tool only. Your money stays with your broker.",
    },
  ];

  return (
    <SimpleCard>
      <h3 className="text-lg font-semibold text-slate-800 mb-5">
        Frequently Asked Questions
      </h3>
      <div className="space-y-5">
        {questions.map((faq, i) => (
          <div
            key={i}
            className="border-b border-slate-100 pb-4 last:border-0 last:pb-0"
          >
            <p className="text-sm font-semibold text-slate-800">{faq.q}</p>
            <p className="text-sm text-slate-600 mt-1 leading-relaxed">
              {faq.a}
            </p>
          </div>
        ))}
      </div>
    </SimpleCard>
  );
}

// ---------------------------------------------------------------------------
// 7. Getting Started — Simplified Checklist
// ---------------------------------------------------------------------------

function GettingStarted() {
  const steps = [
    {
      label: "Open the Intelligence Dashboard",
      detail:
        "This is your starting point. Check the market mood, read the daily summary, and review the stock suggestions.",
    },
    {
      label: "Review each stock suggestion",
      detail:
        "Look at the confidence score, the suggested price, and the stop-loss level. Read the one-line reason. If it makes sense to you, click Approve. If not, click Skip.",
    },
    {
      label: "Place your trades through your broker",
      detail:
        "If you approved a stock, go to your broker app (Zerodha, Dhan, etc.) and place the actual order at the suggested price. The tool does not execute trades for you.",
    },
    {
      label: "Check your Trades page to track positions",
      detail:
        "Open positions, partial exits, and closed trades all show up here. The Safety Monitor runs in the background and alerts you if a stop-loss is hit.",
    },
    {
      label: "Let the system work overnight",
      detail:
        "After market hours, the system automatically updates market mood, writes a summary, and runs improvement experiments. You don't need to do anything.",
    },
    {
      label: "Next morning, repeat from Step 1",
      detail:
        "Check the new daily summary, review fresh stock picks, and manage your existing positions.",
    },
  ];

  return (
    <SimpleCard>
      <h3 className="text-lg font-semibold text-slate-800 mb-1">
        Getting Started — 6 Simple Steps
      </h3>
      <p className="text-xs text-slate-400 mb-5">
        You can be up and running in under 5 minutes
      </p>
      <div className="space-y-4">
        {steps.map((step, idx) => (
          <div key={idx} className="flex items-start gap-3">
            <span className="flex-shrink-0 w-7 h-7 rounded-full bg-teal-600 text-white flex items-center justify-center mt-0.5">
              <span className="text-xs font-bold">{idx + 1}</span>
            </span>
            <div>
              <p className="text-sm font-semibold text-slate-800">
                {step.label}
              </p>
              <p className="text-sm text-slate-500 mt-0.5">{step.detail}</p>
            </div>
          </div>
        ))}
      </div>
    </SimpleCard>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function IntelligenceGuidePage() {
  return (
    <div className="space-y-8">
      {/* Breadcrumb + Header */}
      <div>
        <div className="flex items-center gap-2 mb-0.5">
          <Link
            href="/intelligence"
            className="text-xs text-teal-600 hover:text-teal-700 font-medium"
          >
            Intelligence
          </Link>
          <span className="text-xs text-slate-300">/</span>
          <span className="text-xs text-slate-500">How It Works</span>
        </div>
        <h1 className="text-xl font-semibold text-slate-800">
          How This Tool Works
        </h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Everything you need to know — explained in plain language, no jargon
        </p>
      </div>

      {/* 1. The Big Picture */}
      <WhatIsThisTool />

      {/* 2. Your Daily Routine */}
      <DailyRoutine />

      {/* 3. Each Page Explained */}
      <div className="space-y-3">
        <SectionHeading>What Each Page Does</SectionHeading>
        <PagesExplained />
      </div>

      {/* 4. Behind the Scenes */}
      <div className="space-y-3">
        <SectionHeading>Behind the Scenes</SectionHeading>
        <BehindTheScenes />
      </div>

      {/* 5. Jargon Buster */}
      <JargonBuster />

      {/* 6. FAQ */}
      <FAQ />

      {/* 7. Getting Started */}
      <GettingStarted />

      {/* Footer link back to dashboard */}
      <div className="flex justify-center pb-4">
        <Link
          href="/intelligence"
          className="text-sm text-teal-600 hover:text-teal-700 font-medium"
        >
          ← Back to Intelligence Dashboard
        </Link>
      </div>
    </div>
  );
}
