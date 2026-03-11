"use client";

import Link from "next/link";

// ---------------------------------------------------------------------------
// Section Components
// ---------------------------------------------------------------------------

function SystemOverviewCard() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-3">
        System Overview
      </p>
      <p className="text-sm text-slate-700 leading-relaxed">
        The intelligence layer transforms CTS from a manual scanning tool into a
        self-improving trading system. It has{" "}
        <span className="font-semibold text-slate-800">7 autonomous agents</span>{" "}
        that run on schedule, plus a human-in-the-loop approval flow for entries.
        You remain the final decision-maker on every trade.
      </p>
      <div className="mt-5 bg-slate-50 rounded-lg border border-slate-100 p-4 overflow-x-auto">
        <pre className="text-xs font-mono text-slate-600 leading-relaxed whitespace-pre">
{`Scanner --> Signal Agent --> Setup Cards --> You (Approve/Skip) --> Trade Execution
               ^                                                         |
       AutoOptimize <-- Backtest <-- Learning Agent <-- Post-Mortem <-- Closed Trade`}
        </pre>
      </div>
      <p className="text-[10px] text-slate-400 mt-2">
        The loop runs continuously: scans generate signals, you approve trades,
        closed trades feed back into the learning engine, and AutoOptimize tunes
        parameters overnight.
      </p>
    </div>
  );
}

function PageCard({
  title,
  href,
  what,
  howToUse,
  whenUpdates,
}: {
  title: string;
  href: string;
  what: string;
  howToUse: string;
  whenUpdates: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 hover:border-teal-200 transition-colors">
      <div className="flex items-center justify-between mb-2">
        <Link
          href={href}
          className="text-base font-semibold text-teal-600 hover:text-teal-700"
        >
          {title} &rarr;
        </Link>
      </div>
      <div className="space-y-3 text-sm text-slate-700">
        <div>
          <p className="text-[10px] text-slate-400 font-medium uppercase tracking-wide mb-0.5">
            What
          </p>
          <p className="leading-relaxed">{what}</p>
        </div>
        <div>
          <p className="text-[10px] text-slate-400 font-medium uppercase tracking-wide mb-0.5">
            How to use
          </p>
          <p className="leading-relaxed">{howToUse}</p>
        </div>
        <div>
          <p className="text-[10px] text-slate-400 font-medium uppercase tracking-wide mb-0.5">
            When it updates
          </p>
          <p className="leading-relaxed">{whenUpdates}</p>
        </div>
      </div>
    </div>
  );
}

function ScheduledAgentsTable() {
  const agents = [
    {
      name: "Risk Guardian",
      schedule: "Every 10 min (market hours)",
      description:
        "Monitors open positions, executes stop losses, tracks portfolio risk. Only agent with autonomous SELL permission.",
    },
    {
      name: "Learning Agent",
      schedule: "Every 30 min (market hours)",
      description:
        "Analyzes closed trades, generates post-mortems, updates signal attribution table.",
    },
    {
      name: "Regime Classifier",
      schedule: "4:45 PM IST (weekdays)",
      description:
        "Classifies market regime using ADX, VIX, Hurst exponent. Activates regime-specific parameter bank.",
    },
    {
      name: "CIO Agent",
      schedule: "5:00 PM IST (weekdays)",
      description:
        "Generates daily brief using regime data, recent experiments, open positions, and RAG memory. Sends to Telegram.",
    },
    {
      name: "Corpus Updater",
      schedule: "5:30 PM IST (weekdays)",
      description:
        "Ingests daily market data (VIX, Nifty levels, top movers) into the RAG memory engine.",
    },
    {
      name: "AutoOptimize",
      schedule: "6:00 PM IST (weekdays)",
      description:
        "Starts overnight parameter research loop. Runs until 8:00 AM next day.",
    },
    {
      name: "Shadow Portfolio",
      schedule: "Every 30 min (market hours)",
      description:
        "Updates paper trade exits, tracks shadow portfolio performance.",
    },
  ];

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="px-5 py-3 border-b border-slate-100">
        <h3 className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
          The 7 Scheduled Agents
        </h3>
        <p className="text-[10px] text-slate-400 mt-0.5">
          Autonomous processes that run on a fixed schedule
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[11px] text-slate-400 uppercase tracking-wider border-b border-slate-100">
              <th className="px-5 py-2 font-medium">Agent</th>
              <th className="px-5 py-2 font-medium">Schedule</th>
              <th className="px-5 py-2 font-medium">What It Does</th>
            </tr>
          </thead>
          <tbody>
            {agents.map((agent) => (
              <tr
                key={agent.name}
                className="border-b border-slate-50 hover:bg-slate-50/50"
              >
                <td className="px-5 py-2.5 font-semibold text-slate-800 whitespace-nowrap">
                  {agent.name}
                </td>
                <td className="px-5 py-2.5 font-mono text-xs text-teal-600 whitespace-nowrap">
                  {agent.schedule}
                </td>
                <td className="px-5 py-2.5 text-xs text-slate-600">
                  {agent.description}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function GettingStartedChecklist() {
  const steps = [
    {
      label: "Configure .env",
      detail:
        "Set ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID",
    },
    {
      label: "Seed the knowledge base",
      detail:
        "Run python scripts/populate_corpus_a.py to load methodology docs into RAG",
    },
    {
      label: "Run your first scan",
      detail: "Go to Scanner, run All Scans for today's date",
    },
    {
      label: "Check Intelligence Dashboard",
      detail: "Review regime, brief, and setup cards",
    },
    {
      label: "Approve/Skip setups",
      detail:
        "The shadow portfolio tracks everything regardless of your decision",
    },
    {
      label: "Let AutoOptimize run overnight",
      detail:
        "Start it from the Optimize page or let the scheduler handle it at 6 PM",
    },
    {
      label: "Review results next morning",
      detail:
        "Check experiment history, updated parameters, and daily brief",
    },
    {
      label: "Check Shadow Portfolio weekly",
      detail: "Compare your picks vs the machine's picks",
    },
    {
      label: "Review Attribution monthly",
      detail: "Identify which signals work in which regimes",
    },
  ];

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-4">
        Getting Started Checklist
      </p>
      <div className="space-y-3">
        {steps.map((step, idx) => (
          <div key={idx} className="flex items-start gap-3">
            <span className="flex-shrink-0 w-5 h-5 rounded bg-teal-50 border border-teal-200 flex items-center justify-center mt-0.5">
              <span className="text-teal-600 text-xs font-bold">
                {idx + 1}
              </span>
            </span>
            <div>
              <p className="text-sm font-semibold text-slate-800">
                {step.label}
              </p>
              <p className="text-xs text-slate-500 mt-0.5">{step.detail}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function KeyConceptsSection() {
  const concepts = [
    {
      term: "Composite Score",
      definition:
        "expectancy x sqrt(trade_count) x (1 - max_drawdown_pct). Halved if drawdown exceeds 15%, zeroed if fewer than 8 trades. This is the single metric AutoOptimize maximizes.",
    },
    {
      term: "Regime",
      definition:
        "4 market states detected from ADX trend strength, VIX volatility, Hurst persistence, and price vs 150-SMA. Each regime activates different parameter thresholds so the system adapts to market conditions.",
    },
    {
      term: "Parameter Banks",
      definition:
        "Pre-set parameter adjustments per regime. E.g., Trending Bull tightens entry criteria, High Volatility widens stop tolerances. AutoOptimize tunes these independently per regime.",
    },
    {
      term: "RAG Memory",
      definition:
        "3 knowledge corpora -- A (methodology, static), B (market data, rolling 90 days), C (trade post-mortems, perpetual). Used by the CIO Agent for context-aware daily briefs.",
    },
    {
      term: "Sacred Files",
      definition:
        "backtest_engine.py and trading_rules.py are NEVER modified by any agent. They are the ground truth for evaluating every experiment. Tampering would invalidate all results.",
    },
  ];

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-4">
        Key Concepts
      </p>
      <div className="space-y-4">
        {concepts.map((c) => (
          <div
            key={c.term}
            className="border-b border-slate-100 pb-4 last:border-0 last:pb-0"
          >
            <p className="text-sm font-semibold text-slate-800">{c.term}</p>
            <p className="text-sm text-slate-600 mt-1 leading-relaxed">
              {c.definition}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function IntelligenceGuidePage() {
  return (
    <div className="space-y-6">
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
          <span className="text-xs text-slate-500">Guide</span>
        </div>
        <h1 className="text-xl font-semibold text-slate-800">
          Intelligence Guide
        </h1>
        <p className="text-sm text-slate-500 mt-0.5">
          How the CTS Intelligence Engine works -- from scanning to autonomous
          optimization
        </p>
      </div>

      {/* System Overview */}
      <SystemOverviewCard />

      {/* Pages Explained */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-slate-800 uppercase tracking-wider">
          Pages Explained
        </h2>
        <div className="grid gap-4 md:grid-cols-2">
          <PageCard
            title="Intelligence Dashboard"
            href="/intelligence"
            what="Your daily command center. Shows market regime, optimization status, risk exposure, the CIO daily brief, and top 3 setup cards."
            howToUse="Check every morning before market open. Review the regime (it affects which parameter set is active). Read the daily brief for overnight insights. Review and Approve/Skip the top setup cards."
            whenUpdates="Regime classifies at 4:45 PM IST. Daily brief generates at 5:00 PM IST."
          />
          <PageCard
            title="AutoOptimize"
            href="/intelligence/optimize"
            what="An overnight research loop that tunes the 16 scanning parameters. It picks one parameter, hypothesizes a change using Claude, runs a backtest, and keeps improvements / reverts failures. A tireless research analyst working overnight."
            howToUse="Click Start before you leave for the day (it auto-starts at 6 PM if enabled). Check results next morning. The Keep Rate tells you how productive the research was. Review the experiment history table to see what changed and why."
            whenUpdates="Runs from 6:00 PM to 8:00 AM IST on weekdays. Composite Score = expectancy x sqrt(trade_count) x (1 - max_drawdown). Parameters have hard bounds (BOUNDS dict) -- the system cannot make dangerous changes. Every change is git-committed so you can always revert."
          />
          <PageCard
            title="Shadow Portfolio"
            href="/intelligence/shadow"
            what="Paper-trades EVERY setup card the system generates, regardless of whether you approved or skipped it. After trades close, it compares shadow (machine) vs live (your picks) performance."
            howToUse="Check weekly. The Human Alpha metric tells you if your filtering adds value. If shadow consistently beats live, you may be too conservative. If live beats shadow, your judgment is adding alpha."
            whenUpdates="Shadow Portfolio agent runs every 30 min during market hours. Key metrics: Shadow Win Rate vs Live Win Rate, Human Alpha (positive = your picks are better)."
          />
          <PageCard
            title="Signal Attribution"
            href="/intelligence/attribution"
            what="Tracks win rates broken down by signal type (PPC, NPC, Contraction) AND market regime (Trending Bull, Ranging Quiet, etc.). Tells you which signals work best in which conditions."
            howToUse="Check monthly. The heatmap shows which signal x regime combos are profitable (green) vs unprofitable (red). Use this to adjust your approval decisions -- e.g., if NPC signals in Ranging Quiet markets have a 20% win rate, skip those setups."
            whenUpdates="Updated by the Learning Agent every 30 min during market hours as trades close."
          />
        </div>
      </div>

      {/* Scheduled Agents Table */}
      <ScheduledAgentsTable />

      {/* Getting Started */}
      <GettingStartedChecklist />

      {/* Key Concepts */}
      <KeyConceptsSection />

      {/* Footer link back to dashboard */}
      <div className="flex justify-center pb-4">
        <Link
          href="/intelligence"
          className="text-sm text-teal-600 hover:text-teal-700 font-medium"
        >
          &larr; Back to Intelligence Dashboard
        </Link>
      </div>
    </div>
  );
}
