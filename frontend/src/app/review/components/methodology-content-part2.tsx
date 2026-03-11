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
  const exits = [
    { level: "12R: Extreme", price: "830.32", pct: "Sell 80% remaining", profit: "+229", color: "bg-emerald-600", w: "100%" },
    { level: "8R: Great", price: "753.88", pct: "Sell 40%", profit: "+153", color: "bg-emerald-500", w: "75%" },
    { level: "4R: Normal", price: "677.44", pct: "Sell 20%", profit: "+76", color: "bg-teal-500", w: "50%" },
    { level: "2R: First Target", price: "639.22", pct: "Sell 20%", profit: "+38", color: "bg-blue-500", w: "30%" },
  ];
  return (
    <SectionCard id="taking-profits" number={9} title="Taking Profits (The Exit Framework)">
      <p className="text-sm text-slate-600 leading-relaxed mb-4">
        We sell in pieces as the stock goes higher. Targets use &quot;R&quot; -- multiples of risk.
      </p>
      <div className="bg-slate-50 rounded-xl p-6 mb-6">
        <h4 className="text-xs text-slate-400 font-semibold uppercase tracking-wider mb-4 text-center">
          Profit-Taking Ladder (Entry &#x20b9;601, Risk &#x20b9;19.11/share)
        </h4>
        <div className="space-y-3">
          {exits.map((e, i) => (
            <div key={i} className="flex items-center gap-3">
              <div className="w-28 md:w-40 text-right">
                <p className="text-xs font-bold text-slate-700">{e.level}</p>
                <p className="text-xs font-mono text-slate-500">&#x20b9;{e.price}</p>
              </div>
              <div className="flex-1">
                <div className={`h-8 ${e.color} rounded-lg flex items-center`} style={{ width: e.w }}>
                  <span className="text-xs text-white font-bold px-3">{e.pct}</span>
                </div>
              </div>
              <span className="w-14 text-xs font-mono text-emerald-600 font-bold">&#x20b9;{e.profit}</span>
            </div>
          ))}
          <div className="flex items-center gap-3">
            <div className="w-28 md:w-40 text-right"><p className="text-xs font-bold text-slate-600">Entry</p><p className="text-xs font-mono text-slate-500">&#x20b9;601.00</p></div>
            <div className="flex-1 border-t-2 border-dashed border-slate-400" />
            <span className="w-14 text-xs font-mono text-slate-500">&#x20b9;0</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-28 md:w-40 text-right"><p className="text-xs font-bold text-red-600">Stop Loss</p><p className="text-xs font-mono text-slate-500">&#x20b9;581.89</p></div>
            <div className="flex-1 border-t-2 border-dashed border-red-400" />
            <span className="w-14 text-xs font-mono text-red-600 font-bold">-&#x20b9;19</span>
          </div>
        </div>
      </div>
      <Callout type="tip">
        You do NOT have to sell at every level. If momentum is strong, hold longer. The ladder gives you a plan.
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
      <Callout type="tip">
        Risk 0.5% per trade, 10 losses in a row = 5% account loss. Recoverable. Risk 10% per trade? 5 losses wipes half.
      </Callout>
    </SectionCard>
  );
}

export function Section11DailyRoutine() {
  const blocks = [
    { time: "AM", label: "9:15 AM -- Market Opens", dur: "15 min", clr: "amber", items: ["Wait 10 min for opening chaos", "Check open trades near SL", "Set SL alerts", "Close the app. Go about your day."] },
    { time: "3PM", label: "3:00 PM -- Last 30 Minutes", dur: "30 min", clr: "teal", items: ["Check READY stocks for trigger breaks", "Use calculator for position size", "Place buy order 3:00-3:30 PM", "Nothing triggered? Do nothing."] },
    { time: "EVE", label: "3:30 PM -- Post-Market", dur: "1 hour", clr: "blue", items: ["Run PPC, NPC, Contraction scans", "Review results for watchlist additions", "Update watchlist buckets", "Log market stance"] },
    { time: "SAT", label: "Weekend -- Weekly Review", dur: "2 hours", clr: "slate", items: ["Fill out weekly trading journal", "Review closed trades", "Deeper chart analysis on NEAR/AWAY", "Plan for coming week"] },
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
        The system runs on a simple daily routine -- about 2 hours total. No all-day screen watching.
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
      <Callout type="tip">Total daily time: ~1 hour 45 minutes. Follow the process at specific times.</Callout>
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
        Find Stage 2 stocks building tight bases, buy on breakout with strict position sizing,
        protect with a stop loss, take profits in steps, never over-risk, and review weekly.
      </p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
        {[
          { val: "Stage 2", sub: "Only buy here" }, { val: "0.5%", sub: "Risk per trade" },
          { val: "3:00 PM", sub: "Buy in last 30 min" }, { val: ">2R", sub: "Winners beat losers" },
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
