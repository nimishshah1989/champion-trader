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
// 1. The Big Picture
// ---------------------------------------------------------------------------

export function WhatIsThisTool() {
  return (
    <SimpleCard>
      <h3 className="text-lg font-semibold text-slate-800 mb-3">
        What does this system do?
      </h3>
      <p className="text-sm text-slate-700 leading-relaxed mb-4">
        The Champion Trader System (CTS) is a{" "}
        <span className="font-semibold text-teal-600">
          fully automated swing trading intelligence platform
        </span>
        . Every day, it scans ~464 NSE stocks, identifies setups matching the
        Champion Trader methodology (PPC, NPC, Contraction patterns), and
        manages a virtual paper-trading portfolio to test its decisions.
      </p>
      <p className="text-sm text-slate-700 leading-relaxed mb-4">
        <span className="font-semibold">The system runs autonomously.</span>{" "}
        It scans stocks at market close, generates buy alerts, executes virtual
        trades, monitors stop-losses, and books profits &mdash; all with virtual
        capital. You review results and can use its signals for your own
        real trading decisions.
      </p>
      <p className="text-sm text-slate-700 leading-relaxed mb-4">
        <span className="font-semibold">It improves itself overnight.</span>{" "}
        After market hours, the AutoOptimize engine runs experiments &mdash;
        systematically tweaking scanning parameters and backtesting each change
        against 90 days of data. Changes that improve the composite score are
        kept; the rest are reverted. One AI analysis call per session evaluates
        the batch and guides the next session.
      </p>
      <p className="text-sm text-slate-700 leading-relaxed">
        <span className="font-semibold">Monthly cost: ~&#8377;180 ($2.20).</span>{" "}
        The system uses AI for one strategic analysis per overnight session.
        Everything else &mdash; scanning, regime detection, risk monitoring,
        position sizing, learning notes &mdash; runs on pure math and rules.
        No per-trade AI calls.
      </p>
    </SimpleCard>
  );
}

// ---------------------------------------------------------------------------
// 2. The Full Pipeline
// ---------------------------------------------------------------------------

interface PipelineStep {
  time: string;
  title: string;
  detail: string;
  page: string;
  href: string;
}

export function DailyRoutine() {
  const steps: PipelineStep[] = [
    {
      time: "9:00 AM onwards",
      title: "Exit Monitor watches open positions",
      detail:
        "Every 2 minutes during market hours, the system checks all open trades against their stop-loss and profit targets (2R, NE, GE, EE). If a stop-loss is hit, it generates a SELL alert. If a target is reached, it books the partial exit per the framework.",
      page: "Actions",
      href: "/actions",
    },
    {
      time: "3:00 - 3:30 PM",
      title: "Entry Monitor scans for trigger breaks",
      detail:
        "In the last 30 minutes of market (entry window), the system checks every READY watchlist stock every minute. If price breaks above the trigger level, it generates a BUY alert. Autopilot then auto-executes with virtual capital.",
      page: "Actions",
      href: "/actions",
    },
    {
      time: "4:00 PM",
      title: "Daily Scanner runs PPC + NPC + Contraction scans",
      detail:
        "After market close, all three scan types run across the full NSE universe. Qualifying stocks are auto-added to the watchlist. A parallel baseline scan with frozen default parameters runs for A/B comparison.",
      page: "Pipeline",
      href: "/pipeline",
    },
    {
      time: "4:45 PM",
      title: "Regime Classifier detects market mood",
      detail:
        "Pure math &mdash; no AI. Analyses NIFTY 50 trend, ADX, India VIX, and breadth to classify the market as TRENDING, RANGING, VOLATILE, or BEARISH. This regime affects which parameter bank is active.",
      page: "Intelligence",
      href: "/intelligence",
    },
    {
      time: "5:00 PM",
      title: "CIO Brief summarizes the day",
      detail:
        "Gathers regime, overnight results, open positions, risk status, and top setups into a structured daily brief. The recommendation is rule-based: it checks regime, risk limits, and setup quality to give a clear action call.",
      page: "Intelligence",
      href: "/intelligence",
    },
    {
      time: "6:00 PM - 8:00 AM",
      title: "AutoOptimize runs overnight experiments",
      detail:
        "Runs up to 10 experiments per session. Each experiment: pick a parameter via systematic sweep, modify strategy.py, run a full 90-day backtest, compare composite scores, keep or revert. After all experiments, ONE AI call analyses the batch and logs strategic insights for the next session.",
      page: "Optimize",
      href: "/intelligence/optimize",
    },
  ];

  return (
    <SimpleCard>
      <h3 className="text-lg font-semibold text-slate-800 mb-1">
        The Daily Pipeline
      </h3>
      <p className="text-xs text-slate-400 mb-5">
        Everything runs automatically on the server &mdash; independent of your
        laptop. Here&rsquo;s the sequence.
      </p>
      <div className="space-y-6">
        {steps.map((step, i) => (
          <div key={i} className="flex gap-4">
            <div className="flex-shrink-0 w-7 h-7 rounded-full bg-teal-600 text-white flex items-center justify-center text-xs font-bold">
              {i + 1}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <p className="text-sm font-semibold text-slate-800">
                  {step.title}
                </p>
                <span className="text-[10px] font-mono text-teal-600 bg-teal-50 border border-teal-200 rounded-full px-2 py-0.5">
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
                Go to {step.page} &rarr;
              </Link>
            </div>
          </div>
        ))}
      </div>
    </SimpleCard>
  );
}

// ---------------------------------------------------------------------------
// 3. Each Page Explained
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
        {title} &rarr;
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
        title="Dashboard"
        href="/"
        oneLiner="Morning overview &mdash; system health, open positions, watchlist"
      >
        <p>Your home base. Shows at a glance:</p>
        <ul className="list-disc list-inside text-sm text-slate-600 space-y-1 ml-1">
          <li>
            <strong>System Status</strong> &mdash; Is the server healthy?
            Are scheduled jobs running?
          </li>
          <li>
            <strong>Open Positions</strong> &mdash; Current virtual trades
            with P&amp;L
          </li>
          <li>
            <strong>Watchlist</strong> &mdash; Stocks being monitored for
            entry triggers
          </li>
          <li>
            <strong>Quick Actions</strong> &mdash; Links to pipeline, actions,
            and intelligence
          </li>
        </ul>
      </PageExplainedCard>

      <PageExplainedCard
        title="Pipeline"
        href="/pipeline"
        oneLiner="Scanner + Watchlist Kanban &mdash; the stock discovery engine"
      >
        <p>
          Run manual scans or view today&rsquo;s automated scan results.
          Stocks are organized into a Kanban board:
        </p>
        <ul className="list-disc list-inside text-sm text-slate-600 space-y-1 ml-1">
          <li>
            <strong>READY</strong> &mdash; Trigger level set, waiting for
            breakout
          </li>
          <li>
            <strong>NEAR</strong> &mdash; Close to forming a setup, needs
            another day or two
          </li>
          <li>
            <strong>AWAY</strong> &mdash; Detected pattern but not yet
            actionable
          </li>
        </ul>
        <p className="text-xs text-slate-400 mt-1">
          Daily scanner runs automatically at 4:00 PM IST and auto-populates
          the watchlist via Autopilot.
        </p>
      </PageExplainedCard>

      <PageExplainedCard
        title="Actions"
        href="/actions"
        oneLiner="BUY and SELL alerts generated by the price monitor"
      >
        <p>
          Real-time alert feed. The system generates two types:
        </p>
        <ul className="list-disc list-inside text-sm text-slate-600 space-y-1 ml-1">
          <li>
            <strong>BUY alerts</strong> &mdash; Trigger level broken during
            entry window (3:00-3:30 PM). Shows entry price, stop-loss,
            position size, and targets.
          </li>
          <li>
            <strong>SELL alerts</strong> &mdash; Stop-loss hit or profit
            target reached. Shows exit price, P&amp;L, and R-multiple.
          </li>
        </ul>
        <p className="text-xs text-slate-400 mt-1">
          Autopilot auto-executes alerts with virtual capital. For real
          trades, you execute through your broker.
        </p>
      </PageExplainedCard>

      <PageExplainedCard
        title="Trades"
        href="/trades"
        oneLiner="Full trade log with P&L, R-multiples, and performance stats"
      >
        <p>
          Two tabs: <strong>Trades</strong> (individual trade history) and{" "}
          <strong>Performance</strong> (aggregate stats).
        </p>
        <p>
          Every trade shows entry/exit dates, quantities, partial exits at
          each target level (2R, NE, GE, EE), gross P&amp;L, and R-multiple.
          This is your trade journal.
        </p>
      </PageExplainedCard>

      <PageExplainedCard
        title="Simulation"
        href="/simulation"
        oneLiner="Backtest the strategy against historical data"
      >
        <p>
          <strong>Historical Backtest</strong> &mdash; &ldquo;If I had run
          this system from date X to date Y with &#8377;1,00,000, what would
          have happened?&rdquo; Fetches real OHLCV data for ~464 stocks,
          runs the full PPC scan + entry/exit framework, and produces an
          equity curve with drawdown stats.
        </p>
        <p>
          <strong>Paper Trading</strong> &mdash; Simulate the strategy
          day-by-day on live market data. Process one day at a time.
        </p>
        <p className="text-xs text-slate-400 mt-1">
          AutoOptimize uses backtests internally to score each parameter
          experiment. The composite score formula:
          expectancy &times; &radic;trade_count &times; (1 - max_drawdown).
        </p>
      </PageExplainedCard>

      <PageExplainedCard
        title="Intelligence Hub"
        href="/intelligence"
        oneLiner="Regime, risk status, daily brief, and setup cards"
      >
        <p>Shows 4 things at a glance:</p>
        <ul className="list-disc list-inside text-sm text-slate-600 space-y-1 ml-1">
          <li>
            <strong>Market Regime</strong> &mdash; TRENDING / RANGING /
            VOLATILE / BEARISH. Pure math, no AI.
          </li>
          <li>
            <strong>Risk Status</strong> &mdash; Open risk as % of capital.
            Entry freeze if limit breached.
          </li>
          <li>
            <strong>Daily Brief</strong> &mdash; Structured summary with
            rule-based recommendation.
          </li>
          <li>
            <strong>Top Setups</strong> &mdash; Today&rsquo;s highest-scoring
            stock picks with entry/SL/targets.
          </li>
        </ul>
      </PageExplainedCard>

      <PageExplainedCard
        title="Optimize"
        href="/intelligence/optimize"
        oneLiner="AutoOptimize experiment history and parameter tuning"
      >
        <p>
          The overnight engine that makes the system smarter. Each session:
        </p>
        <ul className="list-disc list-inside text-sm text-slate-600 space-y-1 ml-1">
          <li>
            Runs up to <strong>10 experiments</strong> using a deterministic
            parameter sweep (no AI cost)
          </li>
          <li>
            Each experiment modifies ONE parameter, runs a 90-day backtest,
            compares the composite score
          </li>
          <li>
            Improvements are kept (git committed); no-improvement is reverted
          </li>
          <li>
            After all experiments, <strong>one AI call</strong> analyses the
            full batch and logs strategic insights
          </li>
        </ul>
        <p className="text-xs text-slate-400 mt-1">
          Cost: ~&#8377;8/night ($0.10). Total ~&#8377;180/month ($2.20).
        </p>
      </PageExplainedCard>

      <PageExplainedCard
        title="Attribution"
        href="/intelligence/attribution"
        oneLiner="Which signal types work best in which market regimes?"
      >
        <p>
          A scorecard that tracks win rate and average R-multiple for each
          signal type (PPC, NPC, Contraction) crossed with each market
          regime (Trending, Ranging, Volatile, Bearish).
        </p>
        <p>
          After 20+ trades per combo, the system flags underperforming
          signal-regime pairs for priority re-optimisation.
        </p>
        <p className="text-xs text-slate-400 mt-1">
          Check monthly &mdash; needs enough data to show meaningful patterns.
        </p>
      </PageExplainedCard>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 4. Behind the Scenes &mdash; The 10 Scheduled Jobs
// ---------------------------------------------------------------------------

export function BehindTheScenes() {
  const timers = [
    {
      name: "Exit Monitor",
      simple:
        "Checks all open positions against stop-loss and profit targets. Generates SELL alerts on hits.",
      when: "Every 2 min, 9:00-15:30 IST",
      icon: "E",
    },
    {
      name: "Entry Monitor",
      simple:
        "Checks READY watchlist stocks for trigger-level breakouts. Generates BUY alerts.",
      when: "Every 1 min, 15:00-15:30 IST",
      icon: "B",
    },
    {
      name: "Risk Guardian",
      simple:
        "Monitors total portfolio risk. Freezes new entries if open risk exceeds 10% of capital.",
      when: "Every 10 min, 9:00-15:30 IST",
      icon: "R",
    },
    {
      name: "Daily Scanner",
      simple:
        "Runs PPC + NPC + Contraction scans on ~464 stocks. Auto-populates watchlist. Runs A/B baseline comparison.",
      when: "4:00 PM weekdays",
      icon: "S",
    },
    {
      name: "Regime Classifier",
      simple:
        "Classifies market as TRENDING/RANGING/VOLATILE/BEARISH using NIFTY trend, ADX, VIX. Pure math.",
      when: "4:45 PM weekdays",
      icon: "M",
    },
    {
      name: "CIO Daily Brief",
      simple:
        "Generates structured daily summary with regime, risk, positions, setups, and rule-based recommendation.",
      when: "5:00 PM weekdays",
      icon: "D",
    },
    {
      name: "Learning Agent",
      simple:
        "Writes post-mortem for each closed trade: regime at entry, exit quality, R-multiple, learning insight. Updates signal attribution table.",
      when: "Every 30 min, 9:00-16:00 IST",
      icon: "L",
    },
    {
      name: "Shadow Portfolio",
      simple:
        "Tracks exits on shadow (paper) trades to compare machine suggestions vs human-approved picks.",
      when: "Every 30 min, 9:00-16:00 IST",
      icon: "P",
    },
    {
      name: "Corpus Updater",
      simple:
        "Saves today's market data (index levels, sector performance) to the RAG memory system.",
      when: "5:30 PM weekdays",
      icon: "C",
    },
    {
      name: "AutoOptimize",
      simple:
        "Runs 10 parameter experiments with backtests. One AI call analyses the batch. Keeps improvements, reverts failures.",
      when: "6:00 PM weekdays (overnight)",
      icon: "O",
    },
  ];

  return (
    <SimpleCard>
      <h3 className="text-lg font-semibold text-slate-800 mb-1">
        10 Scheduled Jobs
      </h3>
      <p className="text-sm text-slate-500 mb-2">
        These run automatically on the server. Each is a Python function
        triggered by APScheduler at the specified time. They run independently
        of your laptop.
      </p>
      <p className="text-xs text-slate-400 mb-5">
        Only AutoOptimize uses AI (one call per session, ~$0.10/night).
        Everything else is pure math and rules.
      </p>

      <div className="space-y-3">
        {timers.map((t) => (
          <div
            key={t.name}
            className="flex items-start gap-3 border-b border-slate-100 pb-3 last:border-0 last:pb-0"
          >
            <span className="flex-shrink-0 w-8 h-8 rounded-lg bg-teal-50 border border-teal-200 flex items-center justify-center text-xs font-bold text-teal-700">
              {t.icon}
            </span>
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
