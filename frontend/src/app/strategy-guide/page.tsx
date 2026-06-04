"use client";

export default function StrategyGuidePage() {
  return (
    <div className="p-6 max-w-4xl mx-auto space-y-10">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Strategy Guide</h1>
        <p className="text-muted-foreground mt-1">
          Plain English explanation of what this system is and how it works
        </p>
      </div>

      {/* What is this */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold border-b pb-2">What is CTS?</h2>
        <p className="text-sm leading-relaxed text-muted-foreground">
          CTS (Champion Trader System) is a swing trading toolkit built around Afzal
          Lokhandwala&rsquo;s Champion Trader methodology. It runs two independent
          paper-trading strategies on NSE stocks — the <strong className="text-foreground">v2
          Setup Scanner</strong> and the <strong className="text-foreground">RS EMA
          50×200</strong> — and tracks every entry, exit, and P&L automatically. The
          goal is to build a proven, rules-based track record before deploying real
          capital.
        </p>
      </section>

      {/* Strategy 1 */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold border-b pb-2">
          Strategy 1 — v2 Setup Scanner (Champion Trader)
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="rounded-lg border p-4 space-y-2">
            <h3 className="font-medium text-sm">What kind of stocks does it look for?</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Stocks in <strong className="text-foreground">Stage 2</strong> — an established
              uptrend where the price is above a rising 30-week average. Within that uptrend,
              the stock must be in a <strong className="text-foreground">volatility
              contraction</strong>: the daily price range has been shrinking for several bars,
              meaning the stock is coiling up. This is the &ldquo;base&rdquo; before a
              potential breakout.
            </p>
          </div>

          <div className="rounded-lg border p-4 space-y-2">
            <h3 className="font-medium text-sm">When does it enter a trade?</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              When the stock breaks above the <strong className="text-foreground">high of the
              last 5 days</strong> in the final 30 minutes of the trading session (3:00–3:30 PM
              IST). That confirmed breakout with volume is the entry trigger. Size is always
              split 50/50 — half the position at entry, ready to add the second half on
              confirmation.
            </p>
          </div>

          <div className="rounded-lg border p-4 space-y-2">
            <h3 className="font-medium text-sm">How does it protect capital?</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              The stop loss is set at <strong className="text-foreground">1× TRP below
              entry</strong> (TRP = True Range Percentage, the stock&rsquo;s average daily
              volatility). The stop then <em>ratchets up</em> using a{" "}
              <strong className="text-foreground">5×ATR chandelier trail</strong> — it locks
              in gains as the stock climbs but never moves down. If the stock closes below the
              trail, the trade exits.
            </p>
          </div>

          <div className="rounded-lg border p-4 space-y-2">
            <h3 className="font-medium text-sm">How does it size positions?</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Risk Per Trade (RPT) is fixed at{" "}
              <strong className="text-foreground">0.35% of account value</strong>. The
              formula: Position Size = (Account × RPT%) ÷ TRP. So if TRP is large (volatile
              stock), you buy fewer shares. If TRP is small (calm stock), you buy more. Max
              15 open positions at once; in a bear market, sizes scale down to 25%.
            </p>
          </div>
        </div>

        <div className="rounded-lg bg-muted/50 p-4 space-y-2">
          <h3 className="font-medium text-sm">Minimum criteria for a valid setup</h3>
          <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
            <li>Stock is in Stage 2 (price above rising 30-week MA)</li>
            <li>At least 20 bars of base formation (the coiling phase)</li>
            <li>Average TRP ≥ 2% (too-quiet stocks are skipped)</li>
            <li>Average daily turnover ≥ ₹1 Cr (liquid enough to trade)</li>
            <li>Volatility contracting over the recent bars</li>
          </ul>
        </div>

        <div className="rounded-lg border p-4 space-y-2">
          <h3 className="font-medium text-sm">What does the Pipeline page do?</h3>
          <p className="text-sm text-muted-foreground leading-relaxed">
            The scanner runs every evening at 5:50 PM IST and sorts qualifying stocks into
            three buckets: <strong className="text-foreground">READY</strong> (trigger set,
            watching for the 5-day breakout), <strong className="text-foreground">NEAR</strong>{" "}
            (approaching READY, base still forming), and{" "}
            <strong className="text-foreground">AWAY</strong> (early base stage, monitor only).
            READY stocks show up on the Dashboard. At 3:00 PM the next day, click{" "}
            <em>Refresh Prices</em> on the Actions page to check if any READY stock has
            crossed its trigger.
          </p>
        </div>
      </section>

      {/* Strategy 2 */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold border-b pb-2">
          Strategy 2 — RS EMA 50×200 (Golden Cross)
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="rounded-lg border p-4 space-y-2">
            <h3 className="font-medium text-sm">What is the signal?</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              A <strong className="text-foreground">golden cross</strong>: the 50-day
              Exponential Moving Average (EMA50) crosses above the 200-day EMA. This is a
              classic long-term trend-change signal. The stock must also be above both EMAs
              and pass a basic liquidity check (≥₹5 Cr average daily turnover).
            </p>
          </div>

          <div className="rounded-lg border p-4 space-y-2">
            <h3 className="font-medium text-sm">How does it trade?</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              On the day a golden cross fires, the system enters at the{" "}
              <strong className="text-foreground">closing price</strong> with a fixed position
              value of ₹50,000 per stock. The stop is a{" "}
              <strong className="text-foreground">hard 10% below entry</strong>. There is no
              trailing — if the stock closes below the 10% stop, it exits.
            </p>
          </div>

          <div className="rounded-lg border p-4 space-y-2">
            <h3 className="font-medium text-sm">Portfolio A vs Portfolio B</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Two identical paper portfolios run side-by-side (₹10L each) as an A/B testing
              framework. Right now both have the same settings — they will diverge when
              different parameter variations are tested against each other. You can compare
              results on the <strong className="text-foreground">RS EMA50×200</strong> page.
            </p>
          </div>

          <div className="rounded-lg border p-4 space-y-2">
            <h3 className="font-medium text-sm">When does it run?</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              The EMA scan runs automatically at{" "}
              <strong className="text-foreground">4:30 PM IST</strong> every day after market
              close. It checks all NSE stocks for fresh golden crosses, enters new positions,
              and checks existing ones for stop hits. Results appear on the RS EMA page and a
              Telegram notification is sent.
            </p>
          </div>
        </div>
      </section>

      {/* Daily workflow */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold border-b pb-2">The Daily Workflow</h2>

        <div className="space-y-2">
          {[
            {
              time: "8:45 AM",
              label: "Kite Login Alert",
              desc: "Telegram sends a daily Zerodha login link. Tap it to authorise Kite for the day — required for bar data ingest.",
            },
            {
              time: "9:15 AM",
              label: "Gap-Down Check",
              desc: "The system checks if any open v2 position has opened below its stop due to an overnight gap. Those are exited immediately at open.",
            },
            {
              time: "3:00 – 3:30 PM",
              label: "Entry Window",
              desc: "Open the Dashboard → Actions. Click Refresh Prices. Any READY stock that has crossed its trigger shows a BUY signal with the calculated position size. Click Act to record the entry.",
            },
            {
              time: "4:30 PM",
              label: "RS EMA Scan",
              desc: "Golden cross scan runs automatically for both portfolios. New entries and stop-hit exits are processed and sent via Telegram.",
            },
            {
              time: "5:30 PM",
              label: "Kite Bar Ingest",
              desc: "Today's OHLCV bars for ~1,300 NSE stocks are downloaded from Zerodha and stored. This feeds tomorrow's scanner.",
            },
            {
              time: "5:40 PM",
              label: "v2 Exit Pass",
              desc: "Chandelier stops are checked. Any v2 position whose close is below its 5×ATR trail is exited and P&L is recorded.",
            },
            {
              time: "5:45 PM",
              label: "v2 Entry Pass",
              desc: "Watchlist stocks that broke their 5-day high on today's bar are entered into the paper portfolio.",
            },
            {
              time: "5:50 PM",
              label: "v2 Setup Scan",
              desc: "Full Stage 2 + contraction scan runs over all 1,300 stocks. Results populate the Pipeline board (READY / NEAR / AWAY) for tomorrow.",
            },
          ].map((row) => (
            <div key={row.time} className="flex gap-4 items-start text-sm">
              <span className="w-28 shrink-0 font-mono text-xs text-muted-foreground pt-0.5">
                {row.time}
              </span>
              <div>
                <span className="font-medium">{row.label}</span>
                <span className="text-muted-foreground"> — {row.desc}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Key numbers */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold border-b pb-2">Key Numbers to Know</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "RPT (v2)", value: "0.35%", desc: "Risk per trade" },
            { label: "Max Positions", value: "15", desc: "v2 pipeline" },
            { label: "Min TRP", value: "2%", desc: "Minimum volatility" },
            { label: "Min Base", value: "20 bars", desc: "Base formation" },
            { label: "EMA Position", value: "₹50,000", desc: "Per RS EMA trade" },
            { label: "EMA Stop", value: "10%", desc: "Hard stop from entry" },
            { label: "DD Halt", value: "15%", desc: "Drawdown breaker" },
            { label: "Bear Scale", value: "0.25×", desc: "Position size in bear" },
          ].map((item) => (
            <div key={item.label} className="rounded-lg border p-3 space-y-1">
              <p className="text-xs text-muted-foreground">{item.label}</p>
              <p className="text-xl font-bold">{item.value}</p>
              <p className="text-xs text-muted-foreground">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Glossary */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold border-b pb-2">Glossary</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-2 text-sm">
          {[
            ["Stage 2", "An uptrend: price above a rising 30-week moving average."],
            ["TRP", "True Range Percentage — a stock's average daily volatility as % of price."],
            ["Chandelier Stop", "A trailing stop that ratchets up with the highest high minus 5×ATR. Never moves down."],
            ["R-Multiple", "P&L expressed as multiples of initial risk. +2R = made 2× what you risked."],
            ["Golden Cross", "EMA50 crosses above EMA200 — a long-term bullish signal."],
            ["Volatility Contraction", "Daily price ranges shrinking over recent bars — the stock is coiling."],
            ["ATR", "Average True Range — average daily price range over the last N days."],
            ["RPT", "Risk Per Trade — the maximum % of account you risk on any single trade."],
            ["Paper Trade", "A simulated trade recorded at real prices but with no actual money at stake."],
            ["Drawdown Breaker", "If the portfolio falls 15% from its peak, all new entries are halted."],
          ].map(([term, def]) => (
            <div key={term} className="flex gap-2">
              <span className="font-medium shrink-0 w-40">{term}</span>
              <span className="text-muted-foreground">{def}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
