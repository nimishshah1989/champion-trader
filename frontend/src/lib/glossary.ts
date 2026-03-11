// ---------------------------------------------------------------------------
// CTS Glossary — Centralized trading term definitions
// Used by InfoTooltip and any UI that needs term explanations.
// ---------------------------------------------------------------------------

export interface GlossaryEntry {
  term: string;
  abbreviation?: string;
  definition: string;
  example?: string;
}

// ---------------------------------------------------------------------------
// Master glossary keyed by uppercase short-form identifier.
// ---------------------------------------------------------------------------
export const GLOSSARY: Record<string, GlossaryEntry> = {
  // ── Scan Types ──────────────────────────────────────────────────────────
  PPC: {
    term: "Positive Pivotal Candle",
    abbreviation: "PPC",
    definition:
      "A bullish signal where the day's range expands 1.5x or more above average, the close is in the upper 60% of the range, volume spikes 1.5x or more, and the candle is green.",
    example:
      "RELIANCE prints a PPC when it gaps up on quarterly results with 2x normal volume.",
  },
  NPC: {
    term: "Negative Pivotal Candle",
    abbreviation: "NPC",
    definition:
      "A bearish signal (mirror of PPC) where the day's range expands 1.5x or more, the close is in the lower 40% of the range, volume spikes 1.5x or more, and the candle is red.",
    example:
      "A stock dropping 5% on heavy volume after a poor earnings report is an NPC.",
  },
  CONTRACTION: {
    term: "Base Contraction",
    abbreviation: "CONTRACTION",
    definition:
      "A volatility squeeze where ATR is declining, candles are narrowing, and price is near resistance. The stock is coiling before a potential breakout.",
    example:
      "ASTERDM trading in a 2% range for three weeks after a prior advance signals contraction.",
  },

  // ── Position Sizing ─────────────────────────────────────────────────────
  RPT: {
    term: "Risk Per Trade",
    abbreviation: "RPT",
    definition:
      "The percentage of your total account value that you risk on a single trade. Ranges from 0.2% to 1.0%, with a default of 0.5%.",
    example:
      "On a 5,00,000 account at 0.5% RPT, you risk a maximum of 2,500 per trade.",
  },
  TRP: {
    term: "True Range Percentage",
    abbreviation: "TRP",
    definition:
      "A stock's average daily range expressed as a percentage of its price. Also used as the stop-loss distance. Stocks with TRP below 2.0% are filtered out as untradeable.",
    example:
      "If a stock at 600 has an average daily range of 18 points, its TRP is 3.0%.",
  },
  AV: {
    term: "Account Value",
    abbreviation: "AV",
    definition:
      "Your total trading capital — the base number from which risk per trade and maximum exposure are calculated.",
    example: "If your trading account holds 5,00,000, that is your AV.",
  },
  SL: {
    term: "Stop Loss",
    abbreviation: "SL",
    definition:
      "The exit price if a trade goes against you. Calculated as Entry Price minus the TRP value (in points). The stop loss is never moved down — only up.",
    example:
      "Entry at 601 with TRP of 3.18% (19.1 pts) gives a SL of approximately 582.",
  },
  POSITION_SIZE: {
    term: "Position Size",
    abbreviation: "Position Size",
    definition:
      "The number of shares to buy, calculated from RPT and TRP so that if the stop loss is hit, you lose exactly RPT percent of your account.",
    example:
      "AV 5,00,000 at 0.5% RPT with entry 601 and TRP 3.18% gives a position size of 131 shares.",
  },
  HALF_QTY: {
    term: "Half Quantity",
    abbreviation: "Half Qty",
    definition:
      "50% of the calculated position size. The Champion Trader method always splits entry into two equal halves to manage risk.",
    example:
      "Position size of 131 gives a half quantity of 65 shares per tranche.",
  },

  // ── Exit Targets ────────────────────────────────────────────────────────
  "2R": {
    term: "2R Exit",
    abbreviation: "2R",
    definition:
      "When profit reaches 2x the original risk amount, you exit 20% of your position to lock in gains early.",
    example:
      "Risked 2,500, so at 5,000 profit you sell 20% of your shares.",
  },
  NE: {
    term: "Normal Exit",
    abbreviation: "NE",
    definition:
      "At 4x the TRP distance from entry, you exit another 20% of your position. This is the first target-based exit.",
    example:
      "Entry 601 with TRP 3.18% (19.1 pts) — Normal Exit triggers around 677.",
  },
  GE: {
    term: "Great Exit",
    abbreviation: "GE",
    definition:
      "At 8x the TRP distance from entry, you exit 40% of your position. The trade is performing well.",
    example:
      "Entry 601 with TRP 19.1 pts — Great Exit triggers around 754.",
  },
  EE: {
    term: "Excellent Exit",
    abbreviation: "EE",
    definition:
      "At 12x the TRP distance from entry, you exit 80% of your remaining position. This is a home-run trade.",
    example:
      "Entry 601 with TRP 19.1 pts — Excellent Exit triggers around 830.",
  },

  // ── Stock Analysis ──────────────────────────────────────────────────────
  STAGE: {
    term: "Stock Stage",
    abbreviation: "Stage",
    definition:
      "Where a stock sits in its lifecycle: S1 (basing/accumulation), S1B (late basing — best entry zone), S2 (advancing/uptrend), S3 (topping), S4 (declining).",
    example:
      "A stock trading sideways for months near its lows is in Stage 1. When it breaks out, it enters Stage 2.",
  },
  BASE: {
    term: "Base Pattern",
    abbreviation: "Base",
    definition:
      "A sideways consolidation period where a stock builds a launchpad for a breakout. Minimum 20 bars required. Quality can be Smooth, Mixed, or Choppy.",
    example:
      "ASTERDM consolidating between 580 and 610 for 25 bars forms a smooth base.",
  },
  ADT: {
    term: "Average Daily Turnover",
    abbreviation: "ADT",
    definition:
      "Volume multiplied by price, averaged over 20 days. This liquidity filter ensures the stock trades enough rupees daily to enter and exit positions without slippage.",
    example:
      "A stock at 500 averaging 50,000 shares/day has an ADT of 2.5 Crores.",
  },
  TRP_RATIO: {
    term: "True Range Ratio",
    abbreviation: "TRP Ratio",
    definition:
      "Today's range divided by the 20-day average range. Values above 1.5x indicate unusual range expansion — a potential pivotal signal.",
    example:
      "If average daily range is 12 pts and today's range is 20 pts, TRP Ratio is 1.67.",
  },
  VOL_RATIO: {
    term: "Volume Ratio",
    abbreviation: "Vol Ratio",
    definition:
      "Today's volume divided by the 20-day average volume. Values above 1.5x indicate unusual participation — often paired with range expansion for pivotal candles.",
    example:
      "Average volume 1 lakh shares, today 2 lakh shares gives a Vol Ratio of 2.0.",
  },
  CLOSE_POSITION: {
    term: "Close Position",
    abbreviation: "Close Pos",
    definition:
      "Where the closing price falls within the day's range. 0.0 means it closed at the low, 1.0 at the high. Above 0.6 is considered bullish.",
    example:
      "Day range 500-520, close at 516 gives a close position of 0.8 — bullish.",
  },
  WUC: {
    term: "Wake-Up Call",
    abbreviation: "WUC",
    definition:
      "The type of entry signal that alerts you to a stock. MBB (Mother of all Breakout Bars), BA (Breakout Anticipated), or EF (Entry Follow-through).",
    example:
      "A massive breakout bar with 3x volume is an MBB — the strongest WUC type.",
  },
  TRIGGER: {
    term: "Trigger Level",
    abbreviation: "Trigger",
    definition:
      "The breakout price above which a stock becomes actionable for entry. Set at the top of the base pattern or recent resistance.",
    example:
      "ASTERDM base tops at 610, so the trigger is 610 — enter only if price clears it.",
  },

  // ── Watchlist ───────────────────────────────────────────────────────────
  READY: {
    term: "Ready Bucket",
    abbreviation: "READY",
    definition:
      "Stocks with a mature base (20+ bars), trigger level set, and ready for entry within days. These are your highest-priority watchlist items.",
    example:
      "ASTERDM with a 25-bar base at 610 trigger and strong volume goes into READY.",
  },
  NEAR: {
    term: "Near Bucket",
    abbreviation: "NEAR",
    definition:
      "Stocks with a maturing base (15+ bars) and a trigger forming. These are expected to become READY within 1-2 weeks.",
    example:
      "A stock with 18 bars in base and tightening range moves from AWAY to NEAR.",
  },
  AWAY: {
    term: "Away Bucket",
    abbreviation: "AWAY",
    definition:
      "Stocks in an early-stage base that are worth watching but not ready for entry yet. They need more time to develop a proper base.",
    example:
      "A stock that just started consolidating after a decline — only 8 bars in base.",
  },

  // ── Market ──────────────────────────────────────────────────────────────
  STANCE: {
    term: "Market Stance",
    abbreviation: "Stance",
    definition:
      "Your overall market assessment based on sector strength. Strong (3+ sectors bullish), Moderate (mixed signals), or Weak (3+ sectors bearish).",
    example:
      "If IT, Banking, and Pharma are all in uptrends, Market Stance is Strong.",
  },
  R_MULTIPLE: {
    term: "R-Multiple",
    abbreviation: "R",
    definition:
      "Profit or loss expressed as multiples of the initial risk. +3R means you earned 3x what you risked. -1R means you lost exactly what you risked.",
    example:
      "Risked 2,500 and made 7,500 profit — that is a +3R trade.",
  },
  ARR: {
    term: "Average Risk-Reward",
    abbreviation: "ARR",
    definition:
      "Average winning trade size divided by average losing trade size. Higher is better — it shows how much your winners outpace your losers.",
    example:
      "If average win is 7,500 and average loss is 2,500, your ARR is 3.0.",
  },
  EXPECTANCY: {
    term: "Expectancy",
    abbreviation: "Expectancy",
    definition:
      "The expected return per trade in R-multiples. Calculated as (win_rate x avg_win_R) minus (loss_rate x avg_loss_R). Positive expectancy means your system makes money over time.",
    example:
      "60% win rate at avg +2R wins and -1R losses gives expectancy of +0.8R per trade.",
  },
  WIN_RATE: {
    term: "Win Rate",
    abbreviation: "Win Rate",
    definition:
      "The percentage of your closed trades that were profitable. Important, but meaningless without knowing the R-multiple of wins vs losses.",
    example: "28 winning trades out of 50 total gives a 56% win rate.",
  },
  DRAWDOWN: {
    term: "Maximum Drawdown",
    abbreviation: "Max DD",
    definition:
      "The largest peak-to-trough decline in your account value, expressed as a percentage. A key measure of risk — lower is better.",
    example:
      "Account peaked at 6,00,000 and dropped to 5,40,000 — that is a 10% max drawdown.",
  },

  // ── Intelligence ────────────────────────────────────────────────────────
  REGIME: {
    term: "Market Regime",
    abbreviation: "Regime",
    definition:
      "The current market state detected by the intelligence engine: Trending Bull, Ranging Quiet, High Volatility, or Weakening Bear. Strategy parameters adapt to the regime.",
    example:
      "In a Ranging Quiet regime, the system tightens TRP thresholds and reduces position sizes.",
  },
  COMPOSITE_SCORE: {
    term: "Composite Score",
    abbreviation: "Score",
    definition:
      "A setup quality rating from 0 to 100 that combines base quality, volume pattern, stage, and market context. Higher is better — prioritize setups above 70.",
    example:
      "A smooth 30-bar base with 2x volume breakout in a bull regime scores 88/100.",
  },
  SHADOW: {
    term: "Shadow Portfolio",
    abbreviation: "Shadow",
    definition:
      "A paper-trading portfolio that takes every signal the system generates. It tracks what would have happened if you traded everything, providing a performance baseline.",
    example:
      "Shadow Portfolio took 40 trades this month and returned +12%. You took 15 and returned +8%.",
  },
  HUMAN_ALPHA: {
    term: "Human Alpha",
    abbreviation: "Alpha",
    definition:
      "The difference between your actual selection performance and the Shadow Portfolio. Positive alpha means your filtering adds value over the raw system signals.",
    example:
      "Your portfolio returned +8%, Shadow returned +6% — your Human Alpha is +2%.",
  },
} as const;

// ---------------------------------------------------------------------------
// Helper functions
// ---------------------------------------------------------------------------

/**
 * Look up a glossary entry by its key (case-insensitive).
 * Returns undefined if the key does not exist.
 */
export function getGlossaryEntry(key: string): GlossaryEntry | undefined {
  return GLOSSARY[key.toUpperCase()];
}

/**
 * Return the full display term for a key.
 * Falls back to the original key string when no entry is found.
 */
export function getFullTerm(key: string): string {
  const entry = getGlossaryEntry(key);
  return entry ? entry.term : key;
}
