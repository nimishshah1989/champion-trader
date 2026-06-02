"use client";

import React from "react";
import { SectionCard, Callout } from "./methodology-content";

// ---------------------------------------------------------------------------
// Sections 7-12
// ---------------------------------------------------------------------------

export function Section7PositionSizing() {
  const steps = [
    { title: "Step 1: Your account size", value: "\u20b95,00,000", color: "text-teal-600", desc: "Total money in your trading account." },
    { title: "Step 2: How much you risk", value: "\u20b92,500", color: "text-red-600", desc: "0.5% of account. Even a total failure only loses \u20b92,500.", extra: "(0.5% of \u20b95,00,000)" },
  ];

  return (
    <SectionCard id="position-sizing" number={7} title="Position Sizing (How Much to Buy)">
      <p className="text-sm text-slate-600 leading-relaxed mb-4">
        This answers &quot;How many shares should I buy?&quot; The answer is based on math, not gut feeling.
      </p>
      <Callout type="tip">
        v2 note: the live engine risks <strong>0.35%</strong> per trade (not 0.5%) and runs up to 15
        positions -- smaller, more numerous bets deploy more capital and smooth the equity curve. The
        worked example below uses the 0.5% manual-calculator default; the method is identical, only the
        percentage differs.
      </Callout>
      <div className="bg-slate-50 rounded-xl p-6 mb-6">
        <h4 className="text-sm font-semibold text-slate-800 mb-4">Real Example: Buying &quot;XYZ Ltd&quot;</h4>
        <div className="space-y-3">
          {steps.map((s, i) => (
            <div key={i} className="bg-white rounded-lg p-4 border border-slate-200">
              <div className="flex items-center justify-between mb-1">
                <p className="text-sm font-semibold text-slate-800">{s.title}</p>
                <div className="text-right">
                  <span className={`text-lg font-bold font-mono ${s.color}`}>{s.value}</span>
                  {s.extra && <span className="text-xs text-slate-400 ml-2">{s.extra}</span>}
                </div>
              </div>
              <p className="text-xs text-slate-500">{s.desc}</p>
            </div>
          ))}
          <div className="bg-white rounded-lg p-4 border border-slate-200">
            <div className="flex items-center justify-between mb-1">
              <p className="text-sm font-semibold text-slate-800">Step 3: Stock price and TRP</p>
              <div className="text-right text-sm font-mono text-slate-700">
                <span>Price: <strong>&#x20b9;601</strong></span>{" / "}
                <span>TRP: <strong>3.18%</strong></span>
              </div>
            </div>
            <p className="text-xs text-slate-500">TRP is how much the stock moves per day. 3.18% = &#x20b9;19.11/day.</p>
          </div>
          <div className="bg-white rounded-lg p-4 border border-slate-200">
            <div className="flex items-center justify-between mb-1">
              <p className="text-sm font-semibold text-slate-800">Step 4: Stop loss price</p>
              <span className="text-lg font-bold font-mono text-red-600">&#x20b9;581.89</span>
            </div>
            <p className="text-xs text-slate-600 font-mono bg-slate-50 rounded p-2 mt-1">SL = &#x20b9;601 - (3.18% x &#x20b9;601) = <strong>&#x20b9;581.89</strong></p>
          </div>
          <div className="bg-white rounded-lg p-4 border border-slate-200">
            <div className="flex items-center justify-between mb-1">
              <p className="text-sm font-semibold text-slate-800">Step 5: Number of shares</p>
              <span className="text-lg font-bold font-mono text-teal-600">~131 shares</span>
            </div>
            <p className="text-xs text-slate-600 font-mono bg-slate-50 rounded p-2 mt-1">Shares = &#x20b9;2,500 / &#x20b9;19.11 = <strong>~131</strong></p>
          </div>
          <div className="bg-white rounded-lg p-4 border border-teal-200 bg-teal-50/30">
            <div className="flex items-center justify-between mb-1">
              <p className="text-sm font-semibold text-teal-800">Step 6: Split the buy</p>
              <div className="flex items-center gap-3 text-sm font-bold font-mono text-teal-600">
                <span>65</span><span className="text-slate-300">+</span><span>66</span>
              </div>
            </div>
            <p className="text-xs text-slate-500">Buy 65 first at trigger break. If it closes above, buy remaining 66.</p>
          </div>
        </div>
      </div>
      <Callout type="warning">
        Never decide how many shares to buy based on &quot;feeling.&quot; Always use this calculation.
      </Callout>
    </SectionCard>
  );
}

export function Section8StopLoss() {
  return (
    <SectionCard id="stop-loss" number={8} title="Stop Loss (Protecting Yourself)">
      <p className="text-sm text-slate-600 leading-relaxed mb-6">
        A stop loss is your escape plan. Before you buy, you decide: &quot;If the stock drops to
        THIS price, I sell immediately, no questions asked.&quot;
      </p>
      <div className="bg-slate-50 rounded-xl p-5 mb-6">
        <h4 className="text-sm font-semibold text-slate-800 mb-3">How to Calculate:</h4>
        <div className="bg-white rounded-lg p-4 border border-slate-200 text-center">
          <p className="text-sm font-mono text-slate-700">Stop Loss = Entry Price - TRP Amount</p>
          <p className="text-sm font-mono text-slate-500 mt-2">&#x20b9;601 - &#x20b9;19.11 = <span className="font-bold text-red-600">&#x20b9;581.89</span></p>
        </div>
      </div>
      <h4 className="text-sm font-semibold text-slate-800 mb-3">The 3 Golden Rules:</h4>
      <div className="space-y-3 mb-6">
        {[
          { num: 1, title: "Wait 10 minutes after market opens", desc: "9:15-9:25 AM is chaos. Wait for dust to settle.", color: "amber" },
          { num: 2, title: "NEVER move your stop loss DOWN", desc: "Moving it down means risking more than planned. Small losses become devastating.", color: "red" },
          { num: 3, title: "You CAN move your stop loss UP", desc: "Lock in profits as the stock moves in your favour.", color: "emerald" },
        ].map((rule) => {
          const bgMap = { amber: "bg-amber-50/30 border-amber-200", red: "bg-red-50/30 border-red-200", emerald: "bg-emerald-50/30 border-emerald-200" };
          const btnMap = { amber: "bg-amber-500", red: "bg-red-600", emerald: "bg-emerald-600" };
          return (
            <div key={rule.num} className={`flex items-start gap-3 border ${bgMap[rule.color as keyof typeof bgMap]} rounded-xl p-4`}>
              <span className={`flex-shrink-0 w-8 h-8 ${btnMap[rule.color as keyof typeof btnMap]} text-white rounded-lg flex items-center justify-center text-sm font-bold`}>{rule.num}</span>
              <div>
                <p className="text-sm font-semibold text-slate-800">{rule.title}</p>
                <p className="text-xs text-slate-600 mt-0.5">{rule.desc}</p>
              </div>
            </div>
          );
        })}
      </div>
      <Callout type="danger">
        The number one reason traders blow up is not having a stop loss or not following it. No exceptions.
      </Callout>
    </SectionCard>
  );
}

export function Section9TakingProfits() {
  // 5×ATR ≈ ₹61.7 on ASTERDM (ATR ≈ ₹12.34). The stop ratchets up with the highest high
  // and never moves down. There is no profit ladder — the whole position rides one trail.
  const trail = [
    { hh: "605.00", calc: "605.00 − 61.70 = 543.30", stop: "581.89", note: "Initial 1R holds (trail still below it)" },
    { hh: "648.00", calc: "648.00 − 61.70 = 586.30", stop: "586.30", note: "Trail ratchets above entry — now risk-free" },
    { hh: "700.00", calc: "700.00 − 61.70 = 638.30", stop: "638.30", note: "Locking in profit as it runs" },
    { hh: "760.00", calc: "760.00 − 61.70 = 698.30", stop: "698.30", note: "Stop keeps climbing with the high" },
  ];
  return (
    <SectionCard id="taking-profits" number={9} title="Exits — Riding the Trail (v2)">
      <p className="text-sm text-slate-600 leading-relaxed mb-4">
        v2 takes <strong>no partial profits</strong>. We hold the whole position and let a single
        trailing stop do the work — cut losers fast, let winners run far. Two rules:
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="border border-red-200 bg-red-50/30 rounded-xl p-4">
          <p className="text-sm font-semibold text-red-800 mb-1">1. Close-based stop</p>
          <p className="text-xs text-slate-600 leading-relaxed">
            Exit only if the day <strong>closes</strong> below the stop (or gaps below at the open).
            An intraday dip that recovers by close does NOT exit. A hard intraday stop measured 78%
            premature exits and cut win rate ~10 points — so we wait for the close.
          </p>
        </div>
        <div className="border border-emerald-200 bg-emerald-50/30 rounded-xl p-4">
          <p className="text-sm font-semibold text-emerald-800 mb-1">2. 5×ATR chandelier trail</p>
          <p className="text-xs text-slate-600 leading-relaxed">
            Each day, stop = max(old stop, highest high − 5×ATR). It only ratchets <strong>up</strong>,
            never down. There is no fixed target — the winner exits only when a close falls through
            the trail.
          </p>
        </div>
      </div>
      <div className="bg-slate-50 rounded-xl p-6 mb-6">
        <h4 className="text-xs text-slate-400 font-semibold uppercase tracking-wider mb-4">
          How the stop ratchets (ASTERDM: entry &#x20b9;601, initial SL &#x20b9;581.89, 5&times;ATR &asymp; &#x20b9;61.70)
        </h4>
        <div className="space-y-2">
          {trail.map((r, i) => (
            <div key={i} className="bg-white rounded-lg p-3 border border-slate-200 flex items-center justify-between gap-3">
              <div className="text-xs">
                <span className="text-slate-400">Highest high </span>
                <span className="font-mono font-semibold text-slate-700">&#x20b9;{r.hh}</span>
                <span className="text-slate-400 font-mono ml-2 hidden sm:inline">({r.calc})</span>
              </div>
              <div className="text-right">
                <span className="text-[10px] text-slate-400 uppercase tracking-wide mr-1">stop</span>
                <span className="font-mono font-bold text-red-600">&#x20b9;{r.stop}</span>
                <p className="text-[10px] text-slate-500">{r.note}</p>
              </div>
            </div>
          ))}
          <div className="bg-white rounded-lg p-3 border border-amber-200 bg-amber-50/40">
            <p className="text-xs text-amber-800">
              <strong>Exit:</strong> the first day the stock <strong>closes</strong> below the
              current trail, sell the entire position. No trimming, no targets — one exit.
            </p>
          </div>
        </div>
      </div>
      <Callout type="tip">
        Win rate is only ~35%: most trades lose ~1R, a few win big (avg win ≈ 8R). You cannot pick
        which — so take every signal and let the trail decide. Booking profits early (the old ladder)
        is exactly what caps the winners that pay for everything.
      </Callout>
    </SectionCard>
  );
}

export function Section10RiskManagement() {
  const rules = [
    { val: "1%", title: "Max Risk Per Trade", desc: "Never risk more than 1% on a single trade. Usually 0.5%.", border: "border-red-200", dot: "bg-red-50", dotText: "text-red-600", infoBg: "bg-red-50", infoText: "text-red-700", info: ["Account: \u20b95,00,000", "Max risk: \u20b95,000"] },
    { val: "10%", title: "Max Total Risk", desc: "Never have more than 10% at risk across ALL open trades.", border: "border-amber-200", dot: "bg-amber-50", dotText: "text-amber-600", infoBg: "bg-amber-50", infoText: "text-amber-700", info: ["Account: \u20b95,00,000", "Max total risk: \u20b950,000"] },
  ];
  return (
    <SectionCard id="risk-management" number={10} title="Risk Management (The Safety Rules)">
      <p className="text-sm text-slate-600 leading-relaxed mb-6">Professionals focus on not losing money. Profits follow naturally.</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {rules.map((r, i) => (
          <div key={i} className={`bg-white rounded-xl border-2 ${r.border} p-5 text-center`}>
            <div className={`w-12 h-12 rounded-full ${r.dot} flex items-center justify-center mx-auto mb-3`}>
              <span className={`text-xl font-bold ${r.dotText} font-mono`}>{r.val}</span>
            </div>
            <p className="text-sm font-semibold text-slate-800 mb-1">{r.title}</p>
            <p className="text-xs text-slate-500">{r.desc}</p>
            <div className={`${r.infoBg} rounded-lg p-2 mt-3`}>
              {r.info.map((line, j) => <p key={j} className={`text-xs ${j === r.info.length - 1 ? "font-bold" : ""} ${r.infoText}`}>{line}</p>)}
            </div>
          </div>
        ))}
      </div>
      <Callout type="warning">
        v2 portfolio overlay (automatic): risk <strong>0.35%</strong> per trade, at most <strong>15</strong>
        open positions, <strong>0.25&times;</strong> sizing when the market is below a rising 50-DMA, and a
        <strong> 15%</strong> drawdown breaker that halts new entries (resuming within 7.5% of the peak).
        Open winners keep running through a halt.
      </Callout>
      <Callout type="tip">
        Risk 0.35% per trade, 10 losses in a row = 3.5% account loss. Recoverable. Risk 10% per trade? 5 losses wipes half.
      </Callout>
    </SectionCard>
  );
}

export function Section11DailyRoutine() {
  const blocks = [
    { time: "EVE", label: "After Close (5:30-5:50 PM) -- Automated", dur: "system", clr: "blue", items: ["Ingest Kite-adjusted bars into the store", "Close-based 5xATR exit check on open trades", "Open breakout entries, sized by the risk overlay", "Run the v2 setup scan -> READY watchlist"] },
    { time: "AM", label: "9:15 AM -- Gap Check (Automated)", dur: "system", clr: "amber", items: ["System checks open positions for a gap-down through the stop", "Telegram pings you on any fill", "Otherwise there is nothing to do"] },
    { time: "YOU", label: "Your Daily Glance", dur: "~5 min", clr: "teal", items: ["Open the dashboard: positions + trailing stops", "Check the drawdown-breaker state", "Skim READY setups and any Telegram fills"] },
    { time: "SAT", label: "Weekend -- Weekly Review", dur: "1 hour", clr: "slate", items: ["Fill out the weekly trading journal", "Review closed trades + the equity curve", "Confirm the system behaved as designed", "Plan for the coming week"] },
  ];
  const cm: Record<string, { ring: string; bg: string; text: string }> = {
    amber: { ring: "border-amber-400", bg: "bg-amber-100", text: "text-amber-700" },
    teal: { ring: "border-teal-400", bg: "bg-teal-100", text: "text-teal-700" },
    blue: { ring: "border-blue-400", bg: "bg-blue-100", text: "text-blue-700" },
    slate: { ring: "border-slate-300", bg: "bg-slate-100", text: "text-slate-600" },
  };
  return (
    <SectionCard id="daily-routine" number={11} title="The Daily Routine">
      <p className="text-sm text-slate-600 leading-relaxed mb-6">
        The v2 system runs itself after the close. Your job is oversight, not manual scanning --
        a few minutes a day.
      </p>
      <div className="space-y-0 mb-6">
        {blocks.map((b, idx) => {
          const c = cm[b.clr];
          return (
            <div key={idx} className="flex gap-4">
              <div className="flex flex-col items-center">
                <div className={`w-10 h-10 rounded-full ${c.bg} border-2 ${c.ring} flex items-center justify-center flex-shrink-0`}>
                  <span className={`text-[10px] font-bold ${c.text}`}>{b.time}</span>
                </div>
                {idx < blocks.length - 1 && <div className="w-0.5 flex-1 bg-slate-200" />}
              </div>
              <div className={`${idx < blocks.length - 1 ? "pb-6" : ""} flex-1`}>
                <div className="bg-white rounded-xl border border-slate-200 p-4">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm font-bold text-slate-800">{b.label}</p>
                    <span className={`text-[10px] ${c.bg} ${c.text} rounded-full px-2 py-0.5 font-medium`}>{b.dur}</span>
                  </div>
                  <ul className="text-xs text-slate-600 space-y-1 list-disc list-inside">
                    {b.items.map((item, i) => <li key={i}>{item}</li>)}
                  </ul>
                </div>
              </div>
            </div>
          );
        })}
      </div>
      <Callout type="tip">The scheduler does the scanning, sizing, and exits. You supervise -- about 5 minutes a day, plus a weekly review.</Callout>
    </SectionCard>
  );
}

export function Section12WeeklyJournal() {
  const mistakes = [
    "Did I trade without a stop loss?", "Did I move my stop loss DOWN?",
    "Did I buy a stock NOT in Stage 2?", "Did I risk more than 1% on a single trade?",
    "Did I buy on impulse without checking setup rules?",
  ];
  return (
    <SectionCard id="weekly-journal" number={12} title="The Weekly Journal">
      <p className="text-sm text-slate-600 leading-relaxed mb-6">
        Every weekend, honestly answer questions about your trading week. Not about perfection -- about progress.
      </p>
      <div className="bg-red-50 border border-red-200 rounded-xl p-5 mb-6">
        <h4 className="text-sm font-bold text-red-800 mb-3">The &quot;Grave Mistakes&quot; Checklist</h4>
        <div className="space-y-2">
          {mistakes.map((q, idx) => (
            <div key={idx} className="flex items-center gap-3 bg-white rounded-lg p-3 border border-red-100">
              <div className="w-5 h-5 rounded border-2 border-red-300 flex-shrink-0" />
              <p className="text-sm text-slate-700">{q}</p>
            </div>
          ))}
        </div>
      </div>
      <div className="bg-teal-50 border border-teal-200 rounded-xl p-5 mb-6">
        <h4 className="text-sm font-semibold text-teal-800 mb-3">The Surprising Math</h4>
        <div className="bg-white rounded-lg p-4 border border-teal-100">
          <div className="space-y-2 text-xs font-mono text-slate-700">
            <p>10 trades, risking &#x20b9;2,500 each:</p>
            <p className="text-red-600">6 losses x &#x20b9;2,500 = -&#x20b9;15,000</p>
            <p className="text-emerald-600">4 wins x &#x20b9;5,000 (2R) = +&#x20b9;20,000</p>
            <div className="border-t border-slate-200 pt-2 mt-2">
              <p className="text-base font-bold text-emerald-700">Net profit: +&#x20b9;5,000</p>
              <p className="text-slate-500 font-sans text-[10px] mt-1">Lost 6/10 but still profitable. That is risk management.</p>
            </div>
          </div>
        </div>
      </div>
      <Callout type="tip">Every weekend review makes you 1% better. After a year, a completely different trader.</Callout>
    </SectionCard>
  );
}

// ---------------------------------------------------------------------------
// Final Summary
// ---------------------------------------------------------------------------

export function MethodologySummary() {
  return (
    <div className="bg-teal-50 border border-teal-200 rounded-xl p-6">
      <h3 className="text-base font-bold text-teal-800 mb-3">The Champion Trader Methodology in One Sentence</h3>
      <p className="text-sm text-teal-700 leading-relaxed">
        Find Stage 2 stocks building tight bases, buy the breakout on &ge; 2&times; volume, ride a
        5&times;ATR trailing stop (no profit ladder), size at 0.35% with a 15% drawdown breaker, and
        review weekly.
      </p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
        {[
          { val: "Stage 2", sub: "Only buy here" }, { val: "0.35%", sub: "Risk per trade" },
          { val: "≥ 2× vol", sub: "Breakout gate" }, { val: "5×ATR", sub: "Trailing exit" },
        ].map((item, i) => (
          <div key={i} className="bg-white rounded-lg p-3 border border-teal-100 text-center">
            <p className="text-lg font-bold text-teal-600">{item.val}</p>
            <p className="text-[10px] text-slate-500">{item.sub}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
