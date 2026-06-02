"use client";

import React from "react";

// ---------------------------------------------------------------------------
// Shared sub-components for methodology sections
// ---------------------------------------------------------------------------

export function SectionCard({
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

export function Callout({
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
  const icons = { tip: "Tip", warning: "Caution", danger: "Never Do This" };
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

export function StepFlow({ steps }: { steps: { label: string; detail: string }[] }) {
  return (
    <div className="space-y-0">
      {steps.map((step, index) => (
        <div key={index} className="flex gap-4">
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
// v2 reality — what the live system actually does today (and what it does not)
// ---------------------------------------------------------------------------

export function SectionV2Reality() {
  const happening = [
    { k: "Setup gate", v: "Stage-2 uptrend + volatility contraction + a valid base (≥ 20 bars) + average TRP ≥ 2, then buy the break of the 5-day high." },
    { k: "Entry confirmation", v: "Breakout-day volume ≥ 2× the 50-day average (projected live in the last 30 minutes)." },
    { k: "Stop (close-based)", v: "Exit only on a daily CLOSE below the stop, or a gap-down open. An intraday wick through the stop does NOT exit." },
    { k: "Trail (the edge)", v: "A 5×ATR chandelier that ratchets up with the highest high — there is no fixed profit target; winners ride until the trail is closed through." },
    { k: "Sizing", v: "Risk 0.35% of equity per trade (RPT); up to 15 concurrent positions; idle cash earns ~6.5%." },
    { k: "Bear sizing", v: "New positions sized at 0.25× when the NIFTY 500 is below a rising 50-DMA." },
    { k: "Drawdown breaker", v: "Halt new entries at −15% from the equity peak; resume once back within −7.5%. Open winners keep running." },
    { k: "Data + schedule", v: "Kite-adjusted daily bars (the feed the backtest validated). Fully automated post-close: ingest 17:30 → exit 17:40 → entry 17:45 → scan 17:50, plus a 09:15 gap-down check." },
  ];
  const notHappening = [
    { k: "No profit-taking ladder", v: "The 2R / 4R / 8R / 12R book-and-trim ladder is gone. v2 takes no partial profits — it rides the chandelier trail." },
    { k: "No intraday-touch stops", v: "We no longer sell the instant price dips to the stop. (Hard intraday stops measured 78% premature exits and cut win rate ~10 points.)" },
    { k: "No PPC / NPC / Contraction gating", v: "Those candle patterns are kept only as non-gating labels — they no longer decide what we buy. The v2 setup detector is the gate." },
    { k: "No yfinance feed", v: "Live signals run on the same Kite-adjusted feed as the backtest, not a separate 9-month yfinance pull." },
    { k: "No auto param-tuning", v: "AutoOptimize is frozen, so the validated, parity-gated parameters cannot drift overnight." },
    { k: "No real orders yet", v: "The system is paper-trading behind a kill-switch. Real orders stay gated until a clean 10–15 session paper run reconciles fills." },
  ];

  return (
    <SectionCard id="v2-at-a-glance" number={0} title="The v2 System at a Glance (What Happens — and What Does Not)">
      <p className="text-sm text-slate-600 leading-relaxed mb-2">
        The live system trades the <strong>validated v2 strategy</strong>: a single, parity-gated
        brain that the engine, the scheduler, and this app all call. The beginner sections below
        explain the trading concepts; this card is the precise, current truth of what the machine
        does today.
      </p>
      <Callout type="tip">
        The edge is in the <strong>exit</strong>, not in picking setups: cut losers on a confirmed
        close, and let winners run on a wide trailing stop. Everything below serves that.
      </Callout>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
        <div className="border border-emerald-200 bg-emerald-50/40 rounded-xl p-5">
          <h4 className="text-sm font-bold text-emerald-800 mb-3">Happening now (v2)</h4>
          <div className="space-y-3">
            {happening.map((row) => (
              <div key={row.k}>
                <p className="text-xs font-semibold text-emerald-800">{row.k}</p>
                <p className="text-xs text-slate-600 leading-relaxed">{row.v}</p>
              </div>
            ))}
          </div>
        </div>
        <div className="border border-slate-300 bg-slate-50 rounded-xl p-5">
          <h4 className="text-sm font-bold text-slate-700 mb-3">No longer happening (legacy)</h4>
          <div className="space-y-3">
            {notHappening.map((row) => (
              <div key={row.k}>
                <p className="text-xs font-semibold text-slate-700 line-through decoration-slate-400/70">{row.k}</p>
                <p className="text-xs text-slate-500 leading-relaxed">{row.v}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </SectionCard>
  );
}

// ---------------------------------------------------------------------------
// Sections 1-6
// ---------------------------------------------------------------------------

export function Section1SwingTrading() {
  return (
    <SectionCard id="swing-trading" number={1} title="What is Swing Trading?">
      <p className="text-sm text-slate-600 leading-relaxed mb-4">
        Think of the stock market like an ocean with waves. Some people try to
        ride tiny ripples (day traders -- they buy and sell within minutes).
        Others sit on a boat for years waiting for the tide to rise (long-term
        investors). We do something in the middle:
      </p>
      <p className="text-base font-semibold text-teal-700 mb-6">
        We catch medium-sized waves that last 1 to 4 weeks.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="border border-slate-200 rounded-xl p-4 text-center">
          <p className="text-sm font-semibold text-slate-400">Day Trading</p>
          <p className="text-xs text-slate-400 mt-1">Minutes to hours</p>
          <span className="inline-block mt-2 bg-red-50 text-red-600 rounded-full px-3 py-0.5 text-xs font-medium">Not us</span>
        </div>
        <div className="border-2 border-teal-500 rounded-xl p-4 text-center bg-teal-50/30">
          <p className="text-sm font-bold text-teal-700">Swing Trading</p>
          <p className="text-xs text-teal-600 mt-1">1 to 4 weeks</p>
          <span className="inline-block mt-2 bg-teal-100 text-teal-700 rounded-full px-3 py-0.5 text-xs font-bold">This is us!</span>
        </div>
        <div className="border border-slate-200 rounded-xl p-4 text-center">
          <p className="text-sm font-semibold text-slate-400">Investing</p>
          <p className="text-xs text-slate-400 mt-1">Months to years</p>
          <span className="inline-block mt-2 bg-slate-100 text-slate-500 rounded-full px-3 py-0.5 text-xs font-medium">Not us</span>
        </div>
      </div>
      <Callout type="tip">
        Our goal with each trade: catch a price move of 10% to 30%. Not every
        trade will hit that, but that is what we aim for. Small, focused bets
        with clear entry and exit rules.
      </Callout>
    </SectionCard>
  );
}

export function Section2FourStages() {
  return (
    <SectionCard id="four-stages" number={2} title="The 4 Stages of a Stock (Weinstein Stage Analysis)">
      <p className="text-sm text-slate-600 leading-relaxed mb-4">
        Every stock goes through 4 stages, like the life of a wave. The key to
        making money is buying at the right stage.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div className="border border-slate-200 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-3 h-3 rounded bg-slate-300" />
            <p className="text-sm font-semibold text-slate-800">Stage 1 -- Sleeping</p>
          </div>
          <p className="text-sm text-slate-600 leading-relaxed">
            The stock is moving sideways. Nothing exciting is happening. The price just drifts left and right with no clear direction.
          </p>
        </div>
        <div className="border border-teal-200 bg-teal-50/30 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-3 h-3 rounded bg-emerald-500" />
            <p className="text-sm font-semibold text-teal-800">Stage 2 -- Running (WE BUY HERE)</p>
          </div>
          <p className="text-sm text-slate-600 leading-relaxed">
            The stock is moving upward with energy and volume. The price keeps making higher highs and higher lows. This is the ONLY stage where we buy.
          </p>
        </div>
        <div className="border border-amber-200 bg-amber-50/30 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-3 h-3 rounded bg-amber-400" />
            <p className="text-sm font-semibold text-amber-800">Stage 3 -- Getting Tired</p>
          </div>
          <p className="text-sm text-slate-600 leading-relaxed">
            The stock stops making new highs and starts moving sideways at the top. It looks tempting because the price is high, but do NOT buy.
          </p>
        </div>
        <div className="border border-red-200 bg-red-50/30 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-3 h-3 rounded bg-red-400" />
            <p className="text-sm font-semibold text-red-800">Stage 4 -- Falling</p>
          </div>
          <p className="text-sm text-slate-600 leading-relaxed">
            The stock is going down, making lower lows. Never buy a Stage 4 stock no matter how &quot;cheap&quot; it looks.
          </p>
        </div>
      </div>
      <Callout type="tip">
        The single most important rule: Only buy stocks in Stage 2. If you are
        not sure about the stage, skip it. There are always more opportunities tomorrow.
      </Callout>
    </SectionCard>
  );
}

export function Section3Scanners() {
  return (
    <SectionCard id="scanners" number={3} title="How We Find Stocks to Buy (The Scanners)">
      <p className="text-sm text-slate-600 leading-relaxed mb-6">
        There are thousands of stocks in the market. We use special scans to
        filter down to just a handful that look promising.
      </p>
      <Callout type="warning">
        v2 update: the PPC / NPC / Contraction patterns below are kept only as <strong>labels</strong> --
        they no longer decide what we buy. The real gate is the v2 setup detector: a Stage-2 stock in a
        valid base (&ge; 20 bars), contracting, with average TRP &ge; 2, that breaks its 5-day high on
        &ge; 2&times; volume.
      </Callout>
      <div className="border border-emerald-200 bg-emerald-50/30 rounded-xl p-5 mb-4">
        <div className="flex items-center gap-3 mb-3">
          <span className="bg-emerald-600 text-white text-xs font-bold px-2.5 py-1 rounded">PPC</span>
          <h4 className="text-sm font-semibold text-slate-800">Positive Pivotal Candle</h4>
        </div>
        <p className="text-sm text-slate-600 leading-relaxed">
          A big green candle -- much bigger than normal -- that says &quot;something important just happened here!&quot;
          It is 1.5x bigger than average, closes near the top of its range, and has much higher volume.
        </p>
      </div>
      <div className="border border-red-200 bg-red-50/30 rounded-xl p-5 mb-4">
        <div className="flex items-center gap-3 mb-3">
          <span className="bg-red-600 text-white text-xs font-bold px-2.5 py-1 rounded">NPC</span>
          <h4 className="text-sm font-semibold text-slate-800">Negative Pivotal Candle</h4>
        </div>
        <p className="text-sm text-slate-600 leading-relaxed">
          The opposite of a PPC. A big red candle -- like a fire alarm going off. A warning signal. If you see it in a stock you own, watch your stop loss carefully.
        </p>
      </div>
      <div className="border border-blue-200 bg-blue-50/30 rounded-xl p-5">
        <div className="flex items-center gap-3 mb-3">
          <span className="bg-blue-600 text-white text-xs font-bold px-2.5 py-1 rounded">CONTRACTION</span>
          <h4 className="text-sm font-semibold text-slate-800">Volatility Contraction (The Spring)</h4>
        </div>
        <p className="text-sm text-slate-600 leading-relaxed">
          When a stock gets quieter and quieter -- the candles get smaller, volume dries up. It is building energy for a big move, like pressing a spring down.
        </p>
      </div>
    </SectionCard>
  );
}

export function Section4BasePattern() {
  return (
    <SectionCard id="base-pattern" number={4} title="The Base Pattern (Where Good Setups Form)">
      <p className="text-sm text-slate-600 leading-relaxed mb-4">
        Before a rocket launches, it sits on a launchpad. Before a stock
        explodes upward, it forms a &quot;base&quot; -- a sideways movement that
        lasts at least 20 trading days (about 4 weeks).
      </p>
      <h4 className="text-sm font-semibold text-slate-800 mb-3">What makes a GOOD base?</h4>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
        {[
          { title: "Smooth sideways movement", desc: "Not wild swings, but a calm, tight channel." },
          { title: "Big buyers accumulating", desc: "PPC candles inside the base -- smart money quietly buying." },
          { title: "Volume dries up on red days", desc: "Almost nobody selling on down days. Sellers are exhausted." },
          { title: "Getting tighter (contraction)", desc: "The range narrows over time. The spring is compressing." },
        ].map((item, idx) => (
          <div key={idx} className="flex items-start gap-3 bg-slate-50 rounded-lg p-3">
            <span className="flex-shrink-0 w-6 h-6 bg-emerald-100 text-emerald-700 rounded-full flex items-center justify-center text-xs font-bold">
              {idx + 1}
            </span>
            <div>
              <p className="text-sm font-medium text-slate-800">{item.title}</p>
              <p className="text-xs text-slate-500 mt-0.5">{item.desc}</p>
            </div>
          </div>
        ))}
      </div>
      <Callout type="tip">
        The longer and tighter the base, the more powerful the breakout. A stock
        quiet for 30-40 days is building serious energy. Be patient.
      </Callout>
    </SectionCard>
  );
}

export function Section5WatchlistSystem() {
  return (
    <SectionCard id="watchlist-system" number={5} title="The Watchlist System (READY / NEAR / AWAY)">
      <p className="text-sm text-slate-600 leading-relaxed mb-6">
        Once we find interesting stocks through our scanners, we sort them into
        three buckets. Think of it like a traffic light system:
      </p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="border-2 border-emerald-500 rounded-xl p-5 bg-emerald-50/30">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-4 h-4 rounded-full bg-emerald-500" />
            <h4 className="text-base font-bold text-emerald-700">READY</h4>
          </div>
          <p className="text-sm text-slate-600 leading-relaxed mb-3">
            Ready to launch! Good base, Stage 2, trigger level set. If price breaks above trigger tomorrow, we buy.
          </p>
          <div className="bg-white rounded-lg p-3 border border-emerald-100">
            <p className="text-xs text-emerald-700 font-medium">Set alert. Check daily in last 30 minutes. Be ready to buy.</p>
          </div>
        </div>
        <div className="border-2 border-amber-400 rounded-xl p-5 bg-amber-50/30">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-4 h-4 rounded-full bg-amber-500" />
            <h4 className="text-base font-bold text-amber-700">NEAR</h4>
          </div>
          <p className="text-sm text-slate-600 leading-relaxed mb-3">
            Almost ready. Base forming nicely but needs a few more days. Contraction not tight enough or volume not perfect.
          </p>
          <div className="bg-white rounded-lg p-3 border border-amber-100">
            <p className="text-xs text-amber-700 font-medium">Watch closely this week. Could move to READY in a few days.</p>
          </div>
        </div>
        <div className="border border-slate-200 rounded-xl p-5 bg-slate-50/30">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-4 h-4 rounded-full bg-slate-400" />
            <h4 className="text-base font-bold text-slate-600">AWAY</h4>
          </div>
          <p className="text-sm text-slate-600 leading-relaxed mb-3">
            Good stock but needs more time. Maybe just started building a base or still in Stage 1.
          </p>
          <div className="bg-white rounded-lg p-3 border border-slate-100">
            <p className="text-xs text-slate-500 font-medium">Check back in a few weeks. May take 2-4 weeks to move to NEAR.</p>
          </div>
        </div>
      </div>
      <Callout type="tip">
        A stock moves from AWAY to NEAR to READY as it builds its base and gets
        closer to a breakout. Like watching a fruit ripen -- you wait until it is ready.
      </Callout>
    </SectionCard>
  );
}

export function Section6EntryRules() {
  return (
    <SectionCard id="entry-rules" number={6} title="How We Buy (Entry Rules)">
      <p className="text-sm text-slate-600 leading-relaxed mb-6">
        We do not just randomly buy. There are very specific rules for when and
        how to enter a trade. Think of it like a checklist before a pilot takes off.
      </p>
      <StepFlow
        steps={[
          { label: "Identify the Trigger Level", detail: "The highest point of the last quiet candle in the base. Until the stock crosses this line, we do NOT buy." },
          { label: "Price breaks above the trigger", detail: "When the stock price goes above the trigger level, buy 50% of your planned amount (half your shares)." },
          { label: "Confirm the breakout volume (>= 2x)", detail: "The break must come on at least 2x the 50-day average volume, projected from volume-so-far in the last 30 minutes. A weak-volume break is skipped -- volume is what separates a real breakout from a fake one." },
          { label: "Wait for market close confirmation", detail: "If the stock closes ABOVE the trigger at 3:30 PM, buy the remaining 50%. If it falls back, do not buy the second half." },
          { label: "Only buy in the LAST 30 minutes (3:00-3:30 PM)", detail: "The first few hours are wild. By 3:00 PM, the smart money has shown its hand. We only act in the calm final stretch." },
          { label: "Check for earnings announcements", detail: "Never buy if the company is announcing earnings within the next 3 days. We do not gamble on news." },
        ]}
      />
      <Callout type="warning">
        If you miss the entry at 3:00-3:30 PM, do NOT chase the stock the next
        morning. Wait. If the setup is still valid, it will give you another chance. Discipline is everything.
      </Callout>
    </SectionCard>
  );
}
