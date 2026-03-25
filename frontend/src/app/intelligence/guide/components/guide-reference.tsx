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
// Jargon Buster — Key Terms in Plain Language
// ---------------------------------------------------------------------------

export function JargonBuster() {
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
// FAQ — Common Questions
// ---------------------------------------------------------------------------

export function FAQ() {
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
// Getting Started — Simplified Checklist
// ---------------------------------------------------------------------------

export function GettingStarted() {
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
