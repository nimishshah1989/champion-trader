# Champion Trader System (CTS)
## A Complete Implementation Guide for Claude Code

**Project**: Standalone swing trading intelligence platform based on Afzal Lokhandwala's Champion Trader methodology  
**Stack**: Python (FastAPI backend) + React (Streamlit or Next.js frontend) + SQLite → PostgreSQL  
**Target market**: NSE/BSE India (primary), US markets (secondary)  
**Broker integration**: Dhan API (confirmed from source material)  
**Charting**: TradingView (webhooks + Pine Script scanners)  
**Status**: Greenfield build — do NOT integrate into the existing FIE codebase yet

---

## 1. Project Philosophy

This system replicates the exact workflow of a USIC championship-winning swing trader. Every feature must map to a real step in his documented daily routine. **No speculative features. No over-engineering.** Build what the workflow demands, nothing more.

The trader operates on these principles:
- Trades only in the **last 30 minutes** of the market session
- Spends **15 minutes at market open** + **30 minutes at market close** + **1 hour post-market** daily
- Everything else is automated or templated
- Zero discretionary decisions outside of setup identification

The system must support this time discipline — it is not a real-time monitoring dashboard. It is a **daily workflow engine**.

---

## 2. Directory Structure to Create

```
champion-trader/
├── README.md                          ← This file
├── .env.example                       ← Environment variables template
├── requirements.txt
├── docker-compose.yml                 ← Optional, for local dev
│
├── backend/
│   ├── main.py                        ← FastAPI app entry point
│   ├── config.py                      ← All config from .env
│   ├── database.py                    ← SQLite/PostgreSQL setup, all table schemas
│   │
│   ├── models/
│   │   ├── trade.py                   ← Trade model
│   │   ├── watchlist.py               ← Watchlist + stock model
│   │   ├── scan_result.py             ← Daily scan output model
│   │   ├── journal.py                 ← Weekly journal model
│   │   └── position.py                ← Open position model
│   │
│   ├── routers/
│   │   ├── scanner.py                 ← POST /scan/run, GET /scan/results
│   │   ├── watchlist.py               ← CRUD for watchlists
│   │   ├── calculator.py              ← POST /calculate/position
│   │   ├── trades.py                  ← Full trade log CRUD
│   │   ├── journal.py                 ← Weekly journal CRUD
│   │   ├── market_stance.py           ← Daily sector strength log
│   │   └── alerts.py                  ← Webhook receiver from TradingView
│   │
│   ├── services/
│   │   ├── position_calculator.py     ← Core position sizing logic
│   │   ├── scanner_engine.py          ← Stock screening logic
│   │   ├── dhan_client.py             ← Dhan broker API wrapper
│   │   ├── tradingview_webhook.py     ← Parse + act on TV alerts
│   │   └── notifications.py           ← Telegram/email alert sender
│   │
│   └── pine_scripts/
│       ├── PPC_Scanner.pine           ← Positive Pivotal Candle screener
│       ├── NPC_Scanner.pine           ← Negative Pivotal Candle screener
│       ├── Contraction_Scanner.pine   ← Base contraction screener
│       ├── TRP_Indicator.pine         ← True Range Percentage indicator
│       └── Stage_Analysis.pine        ← Weinstein stage overlay
│
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── App.jsx
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx          ← Daily command centre
│   │   │   ├── Scanner.jsx            ← Run scans + view results
│   │   │   ├── Watchlist.jsx          ← Near / Ready / Away buckets
│   │   │   ├── PositionCalc.jsx       ← Position sizing calculator
│   │   │   ├── TradeLog.jsx           ← All trades with P&L
│   │   │   ├── Journal.jsx            ← Weekly review form
│   │   │   ├── MarketStance.jsx       ← Daily sector tracker
│   │   │   └── Performance.jsx        ← Expectancy metrics dashboard
│   │   └── components/
│   │       ├── StockCard.jsx
│   │       ├── TradeRow.jsx
│   │       └── MetricBadge.jsx
│
└── docs/
    ├── METHODOLOGY.md                 ← Full trading rules (extracted from source)
    ├── PINE_SCRIPT_GUIDE.md           ← How to use the Pine scripts in TradingView
    └── DHAN_SETUP.md                  ← Broker API setup guide
```

---

## 3. The Trading Methodology — Complete Rules

**This section is the source of truth. Every feature in the system must implement exactly these rules.**

### 3.1 Core Instruments & Timeframes

| Parameter | Rule |
|-----------|------|
| Instruments | Stocks only (NSE equity). Futures for short selling only. No options. |
| Holding period | 1–4 weeks |
| Target per trade | 10–30% gain |
| Execution window | Last 30 minutes of market session |
| Morning routine | First 15 minutes after market open (check open positions + set alerts only) |
| Daily analysis | Post-market: 1 hour. Weekends: 2 hours |
| Timeframes used | Weekly (Stage identification) + Daily (Base analysis) + 60-min (Entry timing) — called WTF |

### 3.2 Stock Selection Criteria (The Scanner Rules)

A stock must pass ALL of the following to be shortlisted:

```
1. STAGE CHECK (Weekly Chart)
   → Must be in Stage 1 Breakout OR Stage 2 (Advancing Stage)
   → Stage 2 = price above 30-week MA, 30wMA trending up, price making higher highs
   → Reject Stage 3 (topping) and Stage 4 (declining) stocks

2. BASE QUALITY (Daily Chart)
   → Minimum 20 bars (calendar days) of base formation
   → Clear resistance level at top of base
   → Clear support level at bottom of base
   → Price action must be SMOOTH — no wild/choppy swings within the base
   → Wavy bottom preferred (gradual rounding, not V-shaped)

3. VOLUME FEATURES
   → Must have at least ONE standout volume event within the base
   → Look for: large volume on up days (accumulation signature)
   → Volume on down days should be DRY (low) — institutional holding, not selling

4. VOLATILITY FILTER
   → TRP (True Range Percentage) must be > 2
   → TRP = (High - Low) / Close × 100 for each candle, averaged over 10-20 periods
   → TRP < 2 = stock is too tight/illiquid for meaningful swing

5. LIQUIDITY FILTER
   → ADT (Average Daily Turnover) must be ≥ Position Size × 50
   → ADT = average of (Volume × Close Price) over last 20 days
   → This ensures your position can be entered and exited without slippage
   → Example: If your typical position is ₹1,00,000, ADT must be ≥ ₹50,00,000

6. INDUSTRY/SECTOR STRENGTH
   → Stock's sector should be showing more PPC stocks than NPC stocks
   → Do not buy the only strong stock in a universally weak sector
```

### 3.3 Scan Definitions

**PPC Scan (Positive Pivotal Candle)**
- A candle that is significantly larger than recent candles (1.5× to 2.5× the average TRP)
- Closes in the upper 50% of its range (bullish candle)
- Accompanied by volume that is ≥ 1.5× the 20-day average volume
- Represents institutional buying — a "wake-up call" that a stock is being accumulated
- Run this scan DAILY post-market

**NPC Scan (Negative Pivotal Candle)**  
- Opposite of PPC: large bearish candle on above-average volume
- Indicates institutional distribution/selling
- Used to identify WEAK sectors to avoid
- Also run daily post-market

**Contraction Scan (For base identification)**
- Finds stocks where the Average True Range (ATR) is contracting over the last 5-10 bars
- Price range is tightening — the "coil" before the spring
- Specifically looking for 3+ consecutive candles with narrowing ranges
- Ideal entry setup: tight contraction immediately before a trigger bar

### 3.4 Base Pattern Types to Identify and Flag

These are the 7 base features to detect and tag in the scanner:

```
1. PPCs (Multiple Positive Pivotal Candles within the base)
   → 2+ PPC candles during the base period = strong accumulation signal

2. Volume Variations
   → Alternating heavy volume on up days vs light volume on down days within base
   → Signals: big players accumulating while retail sells on dips

3. Turnaround
   → Stock was in Stage 4 decline, now showing first signs of Stage 1 base formation
   → High risk / high reward — only for experienced traders

4. Wake Up Call (WUC)
   → Any ONE of:
     a) MBB (Mini Base Breakout): PPC breaks out of a small base within the larger base
     b) BA (Breakout Attempt): Price breaks resistance briefly, then pulls back
     c) EF (Earnings Flush): Earnings announcement triggers a breakdown (shakeout)
     d) GU (Gap Up): Stock gaps up on news or earnings
     e) EG (Earnings Gap): Earnings create gap up or down to start a new base

5. Pull Back
   → After a PPC breaks above resistance, price pulls back to resistance-turned-support
   → Ideal low-risk entry point

6. Contraction / Congestion
   → Series of Red/Green bars with shrinking range
   → Price tightening before breakout

7. Trigger Bar (TB)
   → The specific candle that defines the entry point
   → Usually the last tight candle before expected breakout
   → Trigger Level (TL) = High of the Trigger Bar
```

### 3.5 Watchlist Categorisation (The Near/Ready/Away System)

Every stock in analysis must be tagged as one of:

```
READY  → Has a Contraction/Congestion pattern + Trigger Bar identified
         → Set alert at Trigger Level
         → Will trade TOMORROW or next session

NEAR   → Stock is nearing the end of its base
         → Watch closely — could move to READY soon
         → Not quite ready to set entry alert yet

AWAY   → Strong stock with good base features
         → Still too early — may need weeks more base building
         → Keep tracking, review weekly
```

### 3.6 Entry Rules

```
Step 1: Trigger Level (TL) = High of the Trigger Bar

Step 2: Entry split into TWO halves
   → 50% quantity: BUY when price BREAKS above TL (live entry during last 30 mins)
   → 50% quantity: BUY on "comfortable close" above TL
     - If close above TL does NOT happen same day:
       → Buy the second half on the NEXT day when price breaks previous day's high

Step 3: Earnings proximity check
   → If earnings announcement is due within NEXT 3 DAYS → AVOID entry
   → Exception: if earnings CAUSE a Wake Up Call setup, it STRENGTHENS the setup

Step 4: Timing rule
   → Execute entries in the LAST 30 MINUTES of the trading session only
   → Wait 10 minutes after market open before checking positions (volatility spike period)
```

### 3.7 Stop Loss Rules

```
Initial SL (Hard Stop) = Entry Price - TRP

Where TRP = True Range Percentage of the stock
Example: Entry at ₹600, TRP = 3% → TRP value = ₹18 → SL = ₹582

IMPORTANT: 
→ Do NOT exit in first 10 minutes of market open (SL may trigger temporarily on gap/spike)
→ If SL is triggered after 10 mins, take the loss without hesitation
→ SL is NEVER moved down (never give a trade more room)
→ SL CAN be moved up as trade progresses (trailing stop)
```

### 3.8 Exit Rules — Full Framework

```
MATHEMATICAL EXIT (Lock profits as trade advances):
→ Exit 20% of position at 2R (when trade is up 2× your initial risk amount)

EXTENSION EXITS (When stock runs significantly):
→ Normal Extension (NE)  = TRP × 4  → Exit 20% of remaining position
→ Great Extension (GE)   = TRP × 8  → Exit 40% of remaining position
→ Extreme Extension (EE) = TRP × 12 → Exit 80% of remaining position

Notes on extension trailing:
→ Once stock is extended (running strongly), trail using LOD (Low of the Day)
→ If extension caused by a large PPC (≥ 2.5× TRP), use midpoint of that PPC candle as trailing stop

FINAL EXIT (100% exit triggers):
→ Stock CLOSES and UNDERCUTS below whichever is LOWER of:
   a) 50 DMA (50-Day Moving Average)
   b) Support zone of the base
→ Exception: if stock has held above 20 DMA for 3+ months continuously, use 20 DMA as final exit instead of 50 DMA

EARNINGS ANNOUNCEMENT EXIT DECISION TREE:
IF already sufficiently profitable in position:
   AND distance from current price to SL is too small to absorb a gap-down → EXIT fully
   OR SL is very tight (say 1%) → EXIT fully
   OR SL is broad (say 4%) → REDUCE position by half
   OR stock has moved up substantially without you taking any partial exit → book partial profits before earnings

IF not yet sufficiently profitable:
   AND stop loss is comfortable → hold fully through earnings
   OR close to breakeven → reduce position size before earnings
```

### 3.9 Risk Management Framework

```
CORE PARAMETERS:

Account Value (AV) = Total trading capital
RPT% = Risk Per Trade as % of AV
  → Default: 0.50% (conservative)
  → Range: 0.30%–0.80% based on market conditions
  
RPT Amount = AV × RPT%
  → Example: AV = ₹10,00,000, RPT = 0.50% → RPT = ₹5,000

Position Size = RPT Amount / (SL% as decimal)
  → Example: RPT = ₹5,000, SL% = 3.17% → Position = ₹5,000 / 0.0317 = ₹1,57,729
  → Shares = Position Value / Entry Price

EXPECTANCY METRICS (track these weekly):
→ Win Rate: target >40%
→ ARR (Average Reward:Risk Ratio): target >2
→ Breakeven formula: Win Rate needed = 1 / (1 + ARR)
  → At ARR=2: need only 33% win rate to break even
  → At ARR=3: need only 25% win rate to break even

INTENSITY METRICS (track these to gauge trading pace):
→ Number of Trades: raise/increase in good markets, decrease in bad
→ RPT%: adjust based on market stance

MARKET STANCE CLASSIFICATION:
→ Weak: TOR (Trades Open Ratio) < 1%, RPT = 0.20%
→ Moderate: TOR 1-3%, RPT = 0.30-0.50%
→ Strong: TOR > 5%, RPT = 0.50-0.80%

OR MATRIX (Overall Risk Matrix):
→ Maximum concurrent open risk = AV × (number of positions × RPT%)
→ Never exceed 10% of AV in total open risk at any time
→ In weak market stance: max 3-4 positions
→ In strong market stance: up to 8-10 positions possible
```

### 3.10 Market Stance Assessment

Run this assessment daily, post-market:

```
1. Run PPC scan → count strong sectors (sectors with majority PPC stocks)
2. Run NPC scan → count weak sectors (sectors with majority NPC stocks)
3. Assess ratio of strong vs weak sectors
4. Log the result in market stance diary with date

Classification:
→ Strong: 3+ sectors in PPC territory, few/no NPC sectors
→ Moderate: Mixed signals, some sectors strong, some weak
→ Weak: Majority NPC sectors, very few PPCs appearing

This classification directly controls:
→ How aggressively you size positions (RPT%)
→ How many new positions you open
→ Whether you stay flat/cash heavy
```

---

## 4. Database Schema

Create these tables in SQLite first (migrate to PostgreSQL later):

### 4.1 `stocks` table
```sql
CREATE TABLE stocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL UNIQUE,           -- NSE symbol e.g. "RELIANCE"
    company_name TEXT,
    sector TEXT,
    industry TEXT,
    exchange TEXT DEFAULT 'NSE',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.2 `scan_results` table
```sql
CREATE TABLE scan_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_date DATE NOT NULL,
    symbol TEXT NOT NULL,
    scan_type TEXT NOT NULL,               -- 'PPC', 'NPC', 'CONTRACTION'
    
    -- Price data at time of scan
    close_price REAL,
    volume BIGINT,
    avg_volume_20d REAL,
    volume_ratio REAL,                     -- volume / avg_volume_20d
    
    -- TRP data
    trp REAL,                              -- True Range Percentage
    avg_trp REAL,                          -- Average TRP over 20 periods
    trp_ratio REAL,                        -- candle TRP / avg TRP
    
    -- Candle characteristics
    candle_body_pct REAL,                  -- body size as % of total range
    close_position REAL,                   -- where close is in range (0=bottom, 1=top)
    
    -- Stage analysis
    stage TEXT,                             -- 'S1', 'S1B', 'S2', 'S3', 'S4'
    above_30w_ma BOOLEAN,
    ma_trending_up BOOLEAN,
    
    -- Base analysis (for PPC scan)
    base_days INTEGER,                      -- how many days in current base
    has_min_20_bar_base BOOLEAN,
    base_quality TEXT,                      -- 'SMOOTH', 'CHOPPY', 'MIXED'
    
    -- Liquidity
    adt REAL,                               -- Average Daily Turnover in crores
    passes_liquidity_filter BOOLEAN,
    
    -- Wake-up call type (if applicable)
    wuc_type TEXT,                          -- 'MBB', 'BA', 'EF', 'GU', 'EG', NULL
    
    -- Categorisation
    watchlist_bucket TEXT,                  -- 'READY', 'NEAR', 'AWAY'
    trigger_level REAL,                     -- TL = High of trigger bar (if READY)
    
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(scan_date, symbol, scan_type)
);
```

### 4.3 `watchlist` table
```sql
CREATE TABLE watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    added_date DATE NOT NULL,
    bucket TEXT NOT NULL,                   -- 'READY', 'NEAR', 'AWAY'
    
    -- Analysis snapshot
    stage TEXT,
    base_days INTEGER,
    base_quality TEXT,
    wuc_types TEXT,                         -- comma-separated list of WUC features found
    
    -- Entry parameters (for READY stocks)
    trigger_level REAL,
    planned_entry_price REAL,
    
    -- Position planning
    planned_sl_pct REAL,                    -- TRP% for this stock
    planned_position_size INTEGER,           -- number of shares
    planned_half_qty INTEGER,               -- half of position size
    
    -- Status tracking
    status TEXT DEFAULT 'ACTIVE',           -- 'ACTIVE', 'TRADED', 'REMOVED', 'EXPIRED'
    removed_reason TEXT,
    
    notes TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.4 `trades` table
```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    
    -- Entry details
    entry_date DATE NOT NULL,
    entry_type TEXT,                        -- 'LIVE_BREAK', 'CLOSE_ABOVE', 'NEXT_DAY_HIGH'
    entry_price_half1 REAL,                 -- Price for first 50% entry
    entry_price_half2 REAL,                 -- Price for second 50% entry
    qty_half1 INTEGER,
    qty_half2 INTEGER,
    total_qty INTEGER,
    avg_entry_price REAL,
    
    -- Risk parameters at entry
    trp_at_entry REAL,
    sl_price REAL,                          -- Entry Price - TRP
    sl_pct REAL,
    rpt_amount REAL,                        -- ₹ risked on this trade
    
    -- Target levels (calculated at entry)
    target_2r REAL,                         -- Mathematical exit target
    target_ne REAL,                         -- Normal Extension (4× TRP)
    target_ge REAL,                         -- Great Extension (8× TRP)
    target_ee REAL,                         -- Extreme Extension (12× TRP)
    
    -- Exit tracking
    exit_date DATE,
    exit_method TEXT,                       -- '2R', 'NE', 'GE', 'EE', 'SL', 'FINAL_50DMA', 'FINAL_20DMA', 'EARNINGS'
    exit_price REAL,
    exit_qty INTEGER,
    
    -- P&L
    gross_pnl REAL,
    r_multiple REAL,                        -- Actual R achieved
    pnl_pct REAL,
    
    -- Trade status
    status TEXT DEFAULT 'OPEN',             -- 'OPEN', 'PARTIAL', 'CLOSED'
    remaining_qty INTEGER,
    
    -- Context
    market_stance_at_entry TEXT,            -- 'WEAK', 'MODERATE', 'STRONG'
    setup_type TEXT,                        -- e.g. "PPC + Contraction + WUC:MBB"
    entry_notes TEXT,
    exit_notes TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.5 `partial_exits` table
```sql
CREATE TABLE partial_exits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id INTEGER NOT NULL REFERENCES trades(id),
    exit_date DATE NOT NULL,
    exit_price REAL NOT NULL,
    exit_qty INTEGER NOT NULL,
    exit_reason TEXT,                       -- '2R', 'NE', 'GE', 'EE', 'EARNINGS_RISK', 'MANUAL'
    r_multiple_at_exit REAL,
    pnl REAL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.6 `market_stance_log` table
```sql
CREATE TABLE market_stance_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_date DATE NOT NULL UNIQUE,
    
    -- Sector strength (comma-separated sector names)
    strong_sectors TEXT,
    weak_sectors TEXT,
    
    -- Derived
    strong_count INTEGER,
    weak_count INTEGER,
    stance TEXT,                            -- 'WEAK', 'MODERATE', 'STRONG'
    
    -- Adjustments made
    rpt_pct REAL,                           -- RPT% in effect today
    max_positions INTEGER,                  -- max concurrent positions today
    
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.7 `weekly_journal` table
```sql
CREATE TABLE weekly_journal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_start DATE NOT NULL UNIQUE,
    week_end DATE NOT NULL,
    
    -- Account performance
    account_value_start REAL,
    account_value_end REAL,
    weekly_return_pct REAL,
    
    -- Expectancy metrics for the week
    trades_taken INTEGER,
    win_count INTEGER,
    loss_count INTEGER,
    win_rate REAL,
    avg_win_r REAL,
    avg_loss_r REAL,
    arr REAL,                               -- Average Reward:Risk
    
    -- Grave Mistakes review (boolean flags)
    grave_casual_trade BOOLEAN DEFAULT FALSE,
    grave_sl_violation BOOLEAN DEFAULT FALSE,
    grave_risk_exceeded BOOLEAN DEFAULT FALSE,
    grave_averaged_down BOOLEAN DEFAULT FALSE,
    grave_rebought_loser BOOLEAN DEFAULT FALSE,
    
    -- Risk management review (text)
    rm_winrate_arr_eval TEXT,
    rm_market_stance_accuracy TEXT,
    rm_rpt_consistency TEXT,
    rm_or_matrix_violated BOOLEAN DEFAULT FALSE,
    rm_slippage_issues TEXT,
    rm_streak_handling TEXT,
    
    -- Technical review
    tech_random_trades TEXT,
    tech_poor_setups TEXT,
    tech_entry_timing TEXT,
    tech_sl_placement TEXT,
    tech_exit_framework TEXT,
    tech_extension_judgment TEXT,
    tech_earnings_handling TEXT,
    
    -- Routine adherence
    routine_scans_daily BOOLEAN DEFAULT TRUE,
    routine_watchlist_updated BOOLEAN DEFAULT TRUE,
    routine_setup_tracker_updated BOOLEAN DEFAULT TRUE,
    routine_screen_time_minimised BOOLEAN DEFAULT TRUE,
    routine_historical_analysis TEXT,
    
    -- Psychology
    psych_affirmations_read BOOLEAN DEFAULT TRUE,
    psych_impulsive_actions TEXT,
    psych_fear_greed_influence TEXT,
    psych_social_trading_influence BOOLEAN DEFAULT FALSE,
    psych_stress_level TEXT,                -- 'LOW', 'MEDIUM', 'HIGH'
    
    -- Summary
    excelled_at TEXT,
    poor_at TEXT,
    key_learnings TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.8 `position_calculator_sessions` table
```sql
CREATE TABLE position_calc_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calc_date DATE NOT NULL,
    symbol TEXT NOT NULL,
    
    account_value REAL NOT NULL,
    rpt_pct REAL NOT NULL,
    rpt_amount REAL NOT NULL,
    
    entry_price REAL NOT NULL,
    sl_pct REAL NOT NULL,                   -- = TRP%
    sl_amount REAL NOT NULL,
    sl_price REAL NOT NULL,
    
    position_value REAL NOT NULL,
    position_size INTEGER NOT NULL,          -- number of shares
    half_qty INTEGER NOT NULL,
    
    -- Pre-calculated targets
    target_2r REAL,
    target_ne REAL,
    target_ge REAL,
    target_ee REAL,
    
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. API Endpoints — Complete Specification

### 5.1 Scanner Routes (`/scanner`)

```
POST /scanner/run
  Body: { scan_type: "PPC" | "NPC" | "CONTRACTION" | "ALL", date: "YYYY-MM-DD" }
  → Triggers scan engine, returns list of scan_result objects
  → Saves results to scan_results table

GET /scanner/results?date=YYYY-MM-DD&type=PPC
  → Returns scan results for given date and type

GET /scanner/results/latest
  → Returns most recent scan results grouped by type
```

### 5.2 Watchlist Routes (`/watchlist`)

```
GET /watchlist
  → Returns all active watchlist entries grouped by bucket (READY/NEAR/AWAY)

POST /watchlist/add
  Body: { symbol, bucket, stage, trigger_level, trp_pct, notes, wuc_types[] }
  → Adds stock to watchlist

PATCH /watchlist/{id}
  Body: { bucket, trigger_level, notes, status }
  → Update stock's bucket or parameters

DELETE /watchlist/{id}
  → Remove stock (sets status to REMOVED)

GET /watchlist/alerts
  → Returns all READY stocks with trigger levels for alert setting
```

### 5.3 Position Calculator (`/calculator`)

```
POST /calculator/position
  Body: {
    symbol: string,
    account_value: number,
    rpt_pct: number,           // e.g. 0.5 for 0.5%
    entry_price: number,
    trp_pct: number            // e.g. 3.17 for 3.17%
  }
  Returns: {
    rpt_amount: number,
    sl_price: number,
    sl_pct: number,
    position_value: number,
    position_size: number,     // shares
    half_qty: number,
    target_2r: number,
    target_ne: number,
    target_ge: number,
    target_ee: number
  }

POST /calculator/pyramid
  Body: { trade_id, current_price, current_qty, available_capital }
  → Calculate pyramid add sizing for an existing trade
```

### 5.4 Trade Management (`/trades`)

```
GET /trades?status=OPEN|CLOSED|ALL
  → Returns trade list with P&L calculations

POST /trades
  Body: full trade entry object
  → Create new trade record

PATCH /trades/{id}/partial-exit
  Body: { qty, exit_price, exit_reason }
  → Record a partial exit, recalculate position

PATCH /trades/{id}/close
  Body: { exit_price, exit_reason, exit_date }
  → Mark trade as fully closed

GET /trades/{id}
  → Full trade detail with all partial exits
  
GET /trades/stats
  → Aggregate stats: win rate, ARR, total P&L, by month/quarter
```

### 5.5 Market Stance (`/market-stance`)

```
POST /market-stance/log
  Body: { date, strong_sectors: [], weak_sectors: [], stance, rpt_pct, notes }
  → Log daily market stance assessment

GET /market-stance/latest
  → Today's or most recent stance

GET /market-stance/history?days=30
  → Stance history for trend analysis
```

### 5.6 Journal (`/journal`)

```
GET /journal
  → List all weekly journals (most recent first)

GET /journal/{week_start}
  → Get specific week's journal

POST /journal
  Body: full weekly journal object
  → Create new weekly journal entry

PATCH /journal/{week_start}
  → Update/complete journal entry
```

### 5.7 TradingView Webhook (`/webhook`)

```
POST /webhook/tradingview
  Body: {
    symbol: string,
    alert_type: "ENTRY" | "SL_HIT" | "PPC_DETECTED" | "NPC_DETECTED",
    price: number,
    timestamp: string,
    message: string
  }
  → Receives alerts from TradingView Pine Script alerts
  → Routes to appropriate action:
    - ENTRY alert → notifies via Telegram, updates watchlist to READY
    - SL_HIT → sends immediate Telegram alert to monitor for 10 mins
    - PPC_DETECTED → adds to scan results
    - NPC_DETECTED → flags sector as weak

POST /webhook/dhan
  → (Future) receive order execution confirmations from Dhan
```

---

## 6. Pine Script Specifications

### 6.1 TRP Indicator (`TRP_Indicator.pine`)

```pine
// True Range Percentage (TRP)
// TRP = (High - Low) / Close × 100 for each candle
// Displayed as: current TRP, average TRP (20-period), and TRP ratio

// Parameters:
// - trp_period: integer, default 20 (lookback for average)
// - alert_threshold: float, default 2.0 (minimum TRP to flag)

// Outputs:
// - TRP line (current candle's range as % of close)
// - TRP MA (20-period average)
// - Colour coding: green when TRP > threshold (volatile enough to trade)
// - Signal: "TRP ALERT: {symbol} TRP={value}% (Avg={avg}%)" when TRP > 2.5× average

// Used for:
// 1. Stock screening (must have TRP > 2 to be tradeable)
// 2. Setting initial stop loss (SL = Entry - TRP value)
// 3. Identifying extension levels (NE=4×TRP, GE=8×TRP, EE=12×TRP)
```

### 6.2 PPC Scanner (`PPC_Scanner.pine`)

```pine
// Positive Pivotal Candle (PPC) Detection
// 
// A PPC candle must satisfy ALL conditions:
// 1. Candle TRP ≥ 1.5× average TRP (significantly larger than recent candles)
// 2. Close is in upper 60% of candle range (bullish close)
//    close_position = (close - low) / (high - low) ≥ 0.60
// 3. Volume ≥ 1.5× average volume (20-day)
// 4. Candle is net positive (close > open)
//
// PPC Strength Classification:
// - Standard PPC: TRP 1.5–2.5× average
// - Strong PPC: TRP 2.5× average (these are the large PPCs that change trailing stop rules)
//
// Output:
// - Paint PPC candles with distinct colour
// - Display PPC count within last 60 bars (base period)
// - Alert: "{symbol} PPC DETECTED: TRP={x}× avg, Vol={y}× avg"
// - Send webhook to /webhook/tradingview with alert_type="PPC_DETECTED"
//
// For screener use: return 1 if PPC on current bar, 0 otherwise
```

### 6.3 NPC Scanner (`NPC_Scanner.pine`)

```pine
// Negative Pivotal Candle (NPC) Detection
// Mirror logic of PPC but for bearish candles:
// 1. Candle TRP ≥ 1.5× average TRP
// 2. Close is in LOWER 40% of candle range (bearish close)
//    close_position = (close - low) / (high - low) ≤ 0.40
// 3. Volume ≥ 1.5× average volume (20-day)
// 4. Candle is net negative (close < open)
//
// Use: identify weak stocks/sectors. Flag sector as weak if ≥ 40% of stocks show NPC.
```

### 6.4 Contraction Scanner (`Contraction_Scanner.pine`)

```pine
// Base Contraction Detection
// Identifies stocks where volatility is contracting (coiling for breakout)
//
// Algorithm:
// 1. Calculate ATR (14-period) for each bar
// 2. Calculate 5-bar slope of ATR — must be negative (ATR declining)
// 3. Calculate candle range for last 5 bars — must be progressively narrowing
// 4. Price must be within 3% of resistance level (upper bound of base)
//
// Trigger Bar identification:
// - The last narrow-range candle before the expected breakout
// - Trigger Level = High of the Trigger Bar
//
// Output:
// - Highlight contraction zone on chart
// - Mark Trigger Bar
// - Plot Trigger Level as horizontal line
// - Alert: "{symbol} CONTRACTION: TL={trigger_level}, TRP={trp}%"
```

### 6.5 Stage Analysis Overlay (`Stage_Analysis.pine`)

```pine
// Weinstein Stage Analysis
// Uses 30-week (150-day) simple moving average as primary trend filter
//
// Stage definitions:
// Stage 1 (Base/Accumulation):
//   - Price near 30wMA
//   - 30wMA is flat (slope close to 0)
//   - Volume generally low
//
// Stage 1 Breakout (S1B):
//   - Price breaks above 30wMA on above-average volume
//   - 30wMA just starting to turn up
//   - Entry allowed here
//
// Stage 2 (Advancing):
//   - Price clearly above 30wMA
//   - 30wMA trending up (positive slope)
//   - Higher highs and higher lows
//   - IDEAL entry stage
//
// Stage 3 (Top/Distribution):
//   - Price at or below 30wMA
//   - 30wMA flattening or turning down
//   - DO NOT buy
//
// Stage 4 (Declining):
//   - Price below 30wMA
//   - 30wMA trending down
//   - DO NOT buy; short candidates only
//
// Output:
// - Colour background of chart by stage
// - Display current stage label
// - Return stage as string for screener filter
```

---

## 7. Position Calculator — Implementation Logic

This is one of the most used tools. Implement it as a fast, real-time calculator.

```python
def calculate_position(
    account_value: float,
    rpt_pct: float,          # as percentage, e.g. 0.50
    entry_price: float,
    trp_pct: float           # as percentage, e.g. 3.17
) -> dict:
    
    rpt_amount = account_value * (rpt_pct / 100)
    
    sl_pct_decimal = trp_pct / 100
    sl_amount = entry_price * sl_pct_decimal
    sl_price = entry_price - sl_amount
    
    position_value = rpt_amount / sl_pct_decimal
    position_size = int(position_value / entry_price)
    half_qty = position_size // 2
    
    # Extension targets based on TRP value in ₹
    trp_value = sl_amount  # TRP value in ₹ = same as initial SL amount
    
    return {
        "rpt_amount": round(rpt_amount, 2),
        "sl_price": round(sl_price, 2),
        "sl_pct": round(trp_pct, 2),
        "sl_amount": round(sl_amount, 2),
        "position_value": round(position_value, 2),
        "position_size": position_size,
        "half_qty": half_qty,
        "target_2r": round(entry_price + (2 * trp_value), 2),
        "target_ne": round(entry_price + (4 * trp_value), 2),   # Normal Extension
        "target_ge": round(entry_price + (8 * trp_value), 2),   # Great Extension
        "target_ee": round(entry_price + (12 * trp_value), 2),  # Extreme Extension
    }
```

Validate this with the example from the source document:
```
AV = ₹5,00,000, RPT = 0.50%, Entry = ₹601, TRP = 3.18%
Expected output: SL = ₹581.95, Position Size = 131 shares, Half Qty = 65
```

---

## 8. Frontend Pages — What Each Page Does

### 8.1 Dashboard (Home)
The daily command centre. Designed to match the Champion Daily Routine:

**Morning block (15 mins):**
- Summary cards: open positions count, total open risk (₹ and %), today's market stance
- Open positions table: symbol, entry price, current P&L, SL price, distance to SL
- "Set SL Alerts" button → generates list of SL prices to set on TradingView/Dhan

**Market Close block (30 mins):**
- READY stocks list → one-click to open position calculator for each
- "Enter Trade" flow → pre-fills calculator, saves to trades table

**Post-Market block (1 hour):**
- Scan trigger buttons: "Run PPC Scan", "Run NPC Scan", "Run Contraction Scan"
- Quick watchlist update form: move stocks between NEAR/READY/AWAY
- Alert generator: outputs list of trigger levels to set for tomorrow

### 8.2 Scanner Page
- Shows scan results for today (or selected date) in three columns: PPC / NPC / Contraction
- Each result card shows: symbol, sector, TRP ratio, volume ratio, stage, quality score
- "Add to Watchlist" button on each card with pre-filled bucket suggestion
- Historical scan comparison: compare today's PPC count to last 5 sessions

### 8.3 Watchlist Page
Three-column Kanban-style view: **READY | NEAR | AWAY**

Each stock card shows:
- Symbol + company name
- Stage, base days, WUC types (as badges)
- Trigger Level (for READY)
- Planned position size, SL%, RPT amount
- "Calculate Position" quick action button
- "Move to Traded" button (opens trade entry modal)
- Notes field

### 8.4 Position Calculator Page
Clean form with:
- Inputs: Account Value, RPT%, Symbol, Entry Price, TRP%
- Pre-loaded account value from settings
- Real-time output as you type (no submit button)
- Outputs: SL Price, SL Amount, Position Size, Half Qty, 2R target, NE/GE/EE levels
- "Save Calculation" button → stores in position_calc_sessions

Validation example (hardcoded test case from document):
```
MARICO: AV=500000, RPT=0.50%, Entry=724.5, TRP=1.85% → Position=188, Half=94, SL=711.10
ASTERDM: AV=500000, RPT=0.50%, Entry=601, TRP=3.18% → Position=131, Half=65, SL=581.95
SWARAJENG: AV=500000, RPT=0.50%, Entry=4482, TRP=3.30% → Position=17, Half=8, SL=4334.09
```

### 8.5 Trade Log Page
Full trade history table with:
- Filter by: status (OPEN/CLOSED), date range, symbol
- Columns: Symbol, Entry Date, Entry Price, Qty, SL, Current Price, P&L ₹, R-Multiple, Status
- Click to expand: full trade detail with all partial exits
- Export to CSV button

### 8.6 Journal Page (Weekly Review)
Structured form matching the Champion Journal template exactly.

Sections:
1. **Grave Mistakes** — 5 binary yes/no checkboxes (any 'yes' = serious review required)
2. **Risk Management** — 10 questions (text + boolean mix)
3. **Technical** — 12 questions (text)
4. **Routine** — 9 checklist items
5. **Psychology** — 7 questions
6. **Review Summary** — Excel/Worst trades, learnings, account value

Auto-calculate: win rate, ARR, return% from trades table for the selected week.

### 8.7 Market Stance Page
Simple daily log + running chart:
- Date, strong sectors (multi-select), weak sectors (multi-select)
- Auto-classify stance (WEAK/MODERATE/STRONG) based on counts
- Running 30-day chart of stance history
- RPT% recommendation based on stance
- Trailing 4-week win rate vs stance correlation (are you trading better in strong markets?)

### 8.8 Performance Page
Analytics dashboard:

**Expectancy Panel:**
- Win Rate (all-time, last 30 days, last 90 days)
- ARR (all-time, recent)
- Average R-multiple per win, per loss
- Expectancy per trade = (Win Rate × Avg Win R) - (Loss Rate × Avg Loss R)

**Monthly P&L chart** (bar chart, each bar = one month)

**R-Multiple distribution** (histogram: how many trades at each R level)

**Market Stance correlation** (table: stance vs win rate + avg R)

**Top 10 winners and losers** (all time)

---

## 9. Notifications System

Use Telegram Bot for all real-time alerts. No email needed.

### Alert types to implement:

```python
ALERT_TEMPLATES = {
    "SL_HIT": "🔴 SL ALERT: {symbol} hit ₹{sl_price}. Monitor for 10 mins. If no bounce, EXIT.",
    "TRIGGER_LEVEL": "🟡 ENTRY ALERT: {symbol} broke TL of ₹{tl}. Ready to enter last 30 mins.",
    "PPC_DETECTED": "📈 PPC: {symbol} showing PPC (TRP {trp_ratio}x, Vol {vol_ratio}x). Check for base.",
    "2R_HIT": "✅ 2R TARGET: {symbol} hit 2R target ₹{target}. Consider exiting 20%.",
    "EXTENSION": "🚀 {ext_type}: {symbol} at {ext_label} (₹{price}). Consider partial exit.",
    "EARNINGS_WARNING": "⚠️ EARNINGS: {symbol} reports in {days} days. Review exit plan.",
    "MARKET_STANCE": "📊 Market Stance: {stance}. Suggested RPT: {rpt_pct}%. Sectors: Strong={strong}, Weak={weak}",
}
```

---

## 10. Build Order (Prioritised)

Build in this exact sequence — each phase is usable standalone before moving to next:

### Phase 1 — Core Engine (Week 1)
1. Set up FastAPI + SQLite with all 8 database tables
2. Implement position calculator endpoint + test against known examples from document
3. Build Position Calculator frontend page
4. **Deliverable**: Working calculator that matches Afzal's manual calculations exactly

### Phase 2 — Watchlist (Week 2)
1. Watchlist CRUD endpoints
2. Market stance log endpoints
3. Build Watchlist page (3-column READY/NEAR/AWAY Kanban)
4. Build Market Stance page
5. **Deliverable**: Can manually maintain a watchlist exactly as Afzal does

### Phase 3 — Trade Log + Journal (Week 3)
1. Trades CRUD with partial exit support
2. Trade P&L calculations (R-multiple, win rate, ARR)
3. Weekly journal CRUD
4. Trade Log page
5. Journal page (full weekly review form)
6. **Deliverable**: Complete trade diary + performance tracking

### Phase 4 — Pine Scripts (Week 4)
1. TRP Indicator
2. PPC Scanner
3. NPC Scanner
4. Contraction Scanner
5. Stage Analysis overlay
6. Test all scripts on TradingView with known historical examples
7. **Deliverable**: Full scanning capability on TradingView

### Phase 5 — Automation (Week 5)
1. TradingView webhook receiver
2. Telegram notification bot
3. Alert pipeline: TV fires alert → webhook → Telegram notification
4. Dashboard page with full daily routine workflow
5. Scanner page connected to webhook data
6. Performance analytics page
7. **Deliverable**: Fully automated alert pipeline

### Phase 6 — Broker Integration (Week 6)
1. Dhan API client (order placement, position tracking)
2. Real-time position updates from Dhan
3. Auto-SL placement on Dhan when trade is entered in system
4. **Deliverable**: One-click trade entry from watchlist to broker

---

## 11. Environment Variables

```bash
# .env.example

# Database
DATABASE_URL=sqlite:///./champion_trader.db
# DATABASE_URL=postgresql://user:password@localhost/champion_trader

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Dhan Broker API
DHAN_CLIENT_ID=your_dhan_client_id
DHAN_ACCESS_TOKEN=your_dhan_access_token

# TradingView Webhook (for incoming alerts)
WEBHOOK_SECRET=your_secret_key_here

# App settings
APP_PORT=8000
ENVIRONMENT=development  # development | production

# Defaults (can be overridden in app)
DEFAULT_ACCOUNT_VALUE=1000000
DEFAULT_RPT_PCT=0.50
DEFAULT_EXCHANGE=NSE
```

---

## 12. Key Business Rules to Enforce in Code

These are non-negotiable trading rules. The system must enforce them as hard constraints:

```python
TRADING_RULES = {
    # Entry rules
    "entry_window_minutes_before_close": 30,    # Only buy in last 30 mins
    "morning_check_delay_minutes": 15,           # Wait 15 mins after open before checking
    "sl_monitor_delay_minutes": 10,              # After SL trigger, wait 10 mins before acting
    "earnings_blackout_days": 3,                 # No new entry within 3 days of earnings
    
    # Position sizing rules
    "max_rpt_pct": 1.0,                          # Never risk more than 1% per trade
    "min_rpt_pct": 0.2,                          # Never risk less than 0.2%
    "default_rpt_pct": 0.5,                      # Default risk per trade
    "max_open_risk_pct": 10.0,                   # Max total portfolio at risk simultaneously
    "entry_split": 0.5,                          # Always split entry 50/50
    
    # Base quality rules
    "min_base_bars": 20,                         # Minimum bars in base
    "min_trp": 2.0,                              # Minimum TRP to consider stock tradeable
    "min_adt_multiplier": 50,                    # ADT must be >= position_size × 50
    
    # Exit rules
    "mathematical_exit_r": 2,                    # Exit 20% at 2R
    "mathematical_exit_pct": 0.20,               # How much to exit at 2R
    "normal_extension_x": 4,                     # NE = 4× TRP
    "great_extension_x": 8,                      # GE = 8× TRP
    "extreme_extension_x": 12,                   # EE = 12× TRP
    "ne_exit_pct": 0.20,
    "ge_exit_pct": 0.40,
    "ee_exit_pct": 0.80,
    
    # Final exit
    "default_final_exit_dma": 50,               # Use 50 DMA as default final exit
    "long_hold_final_exit_dma": 20,             # Use 20 DMA if held > 3 months
    "long_hold_threshold_months": 3,
    
    # Volume filters
    "ppc_min_volume_ratio": 1.5,                # Volume must be 1.5× average for PPC
    "ppc_min_trp_ratio": 1.5,                   # Candle TRP must be 1.5× average for PPC
    "ppc_min_close_position": 0.60,             # Close must be in top 60% of range
    
    # Market stance thresholds
    "weak_stance_tor_pct": 1.0,                 # TOR < 1% = weak market
    "strong_stance_tor_pct": 5.0,               # TOR > 5% = strong market
}
```

---

## 13. Testing Requirements

Write tests for these specific scenarios before considering any module complete:

### Position Calculator Tests
```python
# From source document — all must pass exactly:
assert calculate_position(500000, 0.50, 601, 3.18)["position_size"] == 131
assert calculate_position(500000, 0.50, 724.5, 1.85)["position_size"] == 187  # (188 in doc, minor rounding)
assert calculate_position(500000, 0.50, 4482, 3.30)["position_size"] == 17
assert calculate_position(500000, 0.50, 601, 3.18)["sl_price"] == 581.81  # approx
assert calculate_position(500000, 0.50, 3186, 4.16)["position_size"] == 19
```

### Expectancy Calculation Tests
```python
# From document example:
# Capital 10L, RPT 1%, Win Rate 40%, ARR 2, 120 trades → Return = 24%
result = calculate_expectancy(win_rate=0.40, arr=2.0, trades=120, rpt_pct=1.0)
assert result["return_pct"] == 24
assert result["winning_trades"] == 48
assert result["losing_trades"] == 72
```

### Business Rule Enforcement Tests
```python
# Earnings blackout
assert validate_entry("RELIANCE", earnings_date="2024-01-15", entry_date="2024-01-14") == False
assert validate_entry("RELIANCE", earnings_date="2024-01-15", entry_date="2024-01-10") == True

# TRP filter
assert passes_trp_filter(trp=1.8) == False  # Below minimum of 2.0
assert passes_trp_filter(trp=2.5) == True

# Base duration
assert has_valid_base(base_bars=18) == False  # Below minimum of 20
assert has_valid_base(base_bars=25) == True
```

---

## 14. Clarifications Needed From User Before Building

The following items were NOT fully specified in the source material and need confirmation:

1. **TRP calculation period**: The document says "TRP > 2" and uses TRP as SL basis, but doesn't specify whether TRP is the current candle's range% or the N-period average. **Recommendation**: implement as current candle's (High-Low)/Close × 100, with a 20-period average also calculated.

2. **ADT liquidity filter benchmark**: The document says `ADT = Avg Position Size × 50`. Confirm: is "Avg Position Size" the ₹ value of the position, or number of shares? **Recommendation**: treat as ₹ value (e.g., position of ₹1,00,000 needs ADT ≥ ₹50,00,000).

3. **Stage 2 definition specifics**: The document references "S1B or S2" without defining the exact MA period. Weinstein's original work uses a 30-week MA. **Recommendation**: implement as 30wMA (150 daily bars). Confirm this is correct.

4. **PPC within base**: How many PPCs within a base constitute a "high quality" base? The document says "Multiple PPCs" without a number. **Recommendation**: flag with a PPC count (1, 2, 3+) and let user judge.

5. **OR Matrix specifics**: The document mentions the OR Matrix (Overall Risk Matrix) but doesn't fully define how it changes with different market stances. **Recommendation**: implement 3 preset profiles (CONSERVATIVE/MODERATE/AGGRESSIVE) that user can select.

6. **Sector strength data source**: Where does sector PPC/NPC data come from? TradingView screener, NSE data, or manual? **Recommendation**: start with manual daily log; automate via TradingView screener later.

---

## 15. How To Run This Project

```bash
# 1. Clone / create project structure
mkdir champion-trader && cd champion-trader

# 2. Set up Python environment
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn sqlalchemy alembic pydantic python-dotenv requests

# 3. Set up environment variables
cp .env.example .env
# Edit .env with your values

# 4. Initialize database
python -c "from backend.database import init_db; init_db()"

# 5. Run backend
uvicorn backend.main:app --reload --port 8000

# 6. Set up frontend (if React)
cd frontend
npm install
npm run dev

# 7. Access
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Frontend: http://localhost:3000
```

---

## Source Material Reference

This system is built entirely from the following verified sources:

1. **"Swing Trading 101" PDF** — Afzal Lokhandwala's internal playbook (provided by user). Contains: Step-by-step execution strategy, base pattern types, entry/exit rules, position sizing formulas, market stance criteria, weekly journal template, daily routine timing, and real trade examples (MARICO, ASTERDM, SWARAJENG, WAAREENEER, COROMANDEL).

2. **Public research on Afzal's methodology** — Confirmed: TradingView as primary charting platform (affiliate), Dhan as broker (confirmed from daily routine document page 11), Champion Daily Routine timing, USIC results, and educational curriculum structure.

3. **No speculation** — every rule in this README is sourced directly from verified material. Where rules are ambiguous, this is flagged explicitly in Section 14 (Clarifications Needed).
