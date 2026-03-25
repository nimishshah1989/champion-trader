"use client";

// ---------------------------------------------------------------------------
// Reference sections: Jargon Buster, FAQ, Getting Started
// ---------------------------------------------------------------------------

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
// Jargon Buster
// ---------------------------------------------------------------------------

export function JargonBuster() {
  const terms = [
    {
      term: "PPC / NPC / Contraction",
      simple:
        "Three types of stock patterns the system scans for. PPC (Positive Price Candle) = a strong green day with high volume near the top of the range. NPC (Negative Price Candle) = the opposite pattern, used as a filter. Contraction = the stock's daily range is narrowing, often a sign it's about to make a big move.",
    },
    {
      term: "Stop-Loss (SL)",
      simple:
        "A safety net price. If a stock falls to this level, the position is exited to limit loss. Calculated as Entry Price minus TRP value. The system never moves a stop-loss down.",
    },
    {
      term: "TRP (True Range Percentage)",
      simple:
        "How volatile a stock is, expressed as a percentage of price. Higher TRP = more volatile = wider stop-loss = smaller position size. Minimum 2.0% to be tradeable.",
    },
    {
      term: "RPT (Risk Per Trade)",
      simple:
        "Percentage of total capital risked on each trade. Default 0.5%. So with 1,00,000 capital, you risk 500 per trade. This determines position size.",
    },
    {
      term: "R-Multiple",
      simple:
        "Profit measured in units of risk. If you risked 500 and made 1,000, that's 2R. If you lost 500, that's -1R. The exit framework targets: 2R (mathematical), 4R (normal extension), 8R (great extension), 12R (extreme extension).",
    },
    {
      term: "Composite Score",
      simple:
        "A single number measuring strategy quality. Formula: expectancy x sqrt(trade_count) x (1 - max_drawdown). The overnight optimizer tries to maximise this. Penalised if drawdown exceeds 15%.",
    },
    {
      term: "Market Regime",
      simple:
        "The system classifies market conditions into 4 modes: TRENDING (strong direction), RANGING (sideways), VOLATILE (big swings), BEARISH (falling). Different parameter banks activate for each regime.",
    },
    {
      term: "Expectancy",
      simple:
        "Expected R per trade, calculated as (Win Rate x Avg Win R) - (Loss Rate x Avg Loss R). Positive means the strategy has an edge over many trades.",
    },
    {
      term: "Autopilot",
      simple:
        "The virtual paper trading engine. Uses 1,00,000 virtual capital, 0.5% RPT, max 5 positions, max 10% open risk. Automatically executes BUY/SELL alerts. No real money involved.",
    },
    {
      term: "AutoOptimize",
      simple:
        "The overnight self-improvement engine. Runs 10 experiments per session, each testing a single parameter change via a full 90-day backtest. One AI call per session analyses results. Cost: ~180/month.",
    },
    {
      term: "Parameter Banks",
      simple:
        "Different sets of scanning thresholds for different market regimes. Like driving settings: highway mode (trending), city mode (ranging), rain mode (volatile). The regime classifier decides which bank is active.",
    },
    {
      term: "A/B Comparison",
      simple:
        "Every day, the scanner runs twice: once with optimised parameters and once with frozen default parameters. This measures whether AutoOptimize improvements are real or just noise.",
    },
    {
      term: "Signal Attribution",
      simple:
        "A scorecard tracking win rate and average R for each signal type (PPC, NPC, Contraction) in each market regime. Flags underperforming combos after 20+ trades.",
    },
  ];

  return (
    <SimpleCard>
      <h3 className="text-lg font-semibold text-slate-800 mb-1">
        Jargon Buster
      </h3>
      <p className="text-xs text-slate-400 mb-5">
        Every technical term explained in plain language
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
// FAQ
// ---------------------------------------------------------------------------

export function FAQ() {
  const questions = [
    {
      q: "Does this system trade real money?",
      a: "No. The Autopilot runs on virtual capital (1,00,000). It generates alerts and executes paper trades to test the strategy. For real trading, you use the signals as input and execute through your own broker.",
    },
    {
      q: "What runs automatically without my laptop?",
      a: "Everything. The system runs on a cloud server (EC2) with 10 scheduled jobs via APScheduler. It scans stocks, monitors positions, classifies market regime, generates briefs, runs overnight optimisation, and manages the virtual portfolio. All independent of your laptop.",
    },
    {
      q: "How does the system learn and improve?",
      a: "Three feedback loops: (1) AutoOptimize runs 10 parameter experiments per night, backtesting each change and keeping improvements. (2) The Learning Agent writes a post-mortem for every closed trade, tracking which signal types work in which regimes. (3) Signal Attribution flags underperforming patterns after 20+ trades.",
    },
    {
      q: "What does the AI actually do?",
      a: "Very little. AI makes ONE call per overnight session (~$0.10) to analyse the batch of 10 experiment results and suggest strategic direction. Everything else — scanning, regime detection, risk monitoring, position sizing, exit framework, learning notes, daily brief — is pure math and rule-based logic.",
    },
    {
      q: "How much does it cost to run?",
      a: "About $2.20/month for AI calls (22 trading days x $0.10/session). The EC2 server cost is separate (infrastructure). No per-scan, per-trade, or per-alert AI charges.",
    },
    {
      q: "What is the exit framework?",
      a: "When a trade hits 2R profit: sell 20% (mathematical exit). At 4R: sell 20% (normal extension). At 8R: sell 40% (great extension). At 12R: sell 80% (extreme extension). Stop-loss trails up after each target. Remaining position exits when price closes below 50-day DMA.",
    },
    {
      q: "What's the difference between Simulation and AutoOptimize?",
      a: "Simulation is a tool YOU use to manually test the strategy over any date range. AutoOptimize uses backtests AUTOMATICALLY overnight to test parameter changes. Same engine underneath, different purpose.",
    },
    {
      q: "How does the A/B comparison work?",
      a: "Each day, the scanner runs twice: once with the current optimised parameters and once with frozen default parameters (never changed). The daily comparison shows whether the optimiser's changes are actually helping or hurting.",
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
// Getting Started
// ---------------------------------------------------------------------------

export function GettingStarted() {
  const steps = [
    {
      label: "Check the Dashboard",
      detail:
        "See system health, open positions, and watchlist at a glance. Verify all 10 scheduled jobs are running.",
    },
    {
      label: "Review the Intelligence Hub",
      detail:
        "Check today's market regime, risk status, and the daily brief. See if there are any high-scoring setups.",
    },
    {
      label: "Monitor the Pipeline",
      detail:
        "View scan results from 4:00 PM. READY stocks will be checked for trigger breaks in tomorrow's entry window (3:00-3:30 PM).",
    },
    {
      label: "Watch Actions for BUY/SELL alerts",
      detail:
        "The price monitor generates alerts automatically. Autopilot executes them with virtual capital. You can use these signals for your real broker trades.",
    },
    {
      label: "Review Trades for P&L tracking",
      detail:
        "All virtual trades with entry/exit, partial exits, R-multiples, and gross P&L. Use the Performance tab for aggregate stats.",
    },
    {
      label: "Check Optimize results each morning",
      detail:
        "See how many overnight experiments were run, how many improved the composite score, and read the AI session analysis.",
    },
  ];

  return (
    <SimpleCard>
      <h3 className="text-lg font-semibold text-slate-800 mb-1">
        Getting Started
      </h3>
      <p className="text-xs text-slate-400 mb-5">
        The system runs autonomously. Here&rsquo;s how to monitor it.
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
