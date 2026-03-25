# Champion Trader System (CTS)

## Project Overview
Swing trading intelligence platform based on Afzal Lokhandwala's Champion Trader methodology.
Full specification: `README.md` (1336 lines — the source of truth for all trading rules).

## Tech Stack
- **Backend**: Python FastAPI + SQLite (SQLAlchemy ORM)
- **Frontend**: Next.js 14+ (App Router) + TypeScript + Tailwind CSS + shadcn/ui
- **Database**: SQLite for dev, PostgreSQL later
- **Broker**: Dhan API (future integration)
- **Charting**: TradingView (Pine Scripts + webhooks)
- **Notifications**: Telegram Bot

## Project Structure
```
afzal/                        # Project root
├── backend/                  # FastAPI backend
│   ├── main.py               # App entry point (port 8000)
│   ├── config.py             # Pydantic Settings from .env
│   ├── database.py           # SQLAlchemy + 8 table schemas
│   ├── models/               # Pydantic request/response schemas
│   ├── routers/              # API route handlers
│   ├── services/             # Business logic
│   └── pine_scripts/         # TradingView Pine Script files
├── frontend/                 # Next.js app (port 3000)
│   └── src/app/              # App Router pages
├── docs/                     # Documentation
├── venv/                     # Python virtual environment
└── champion_trader.db        # SQLite database (git-ignored)
```

## Key Commands
```bash
# Backend
source venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000

# Frontend
cd frontend && pnpm dev

# Database
python -c "from backend.database import init_db; init_db()"
```

## Database Tables (21 total)
1. `stocks` — Stock master data (NSE symbols)
2. `scan_results` — Daily PPC/NPC/Contraction scan outputs
3. `watchlist` — READY/NEAR/AWAY categorised stocks
4. `trades` — Full trade lifecycle with partial exits
5. `partial_exits` — Individual partial exit records per trade
6. `market_stance_log` — Daily sector strength assessment
7. `weekly_journal` — Weekly self-review (Champion Journal format)
8. `position_calc_sessions` — Saved position sizing calculations
10. `app_alerts` — UI notification alerts
11. `action_alerts` — BUY/SELL action alerts from price monitor
12. `simulation_runs` — Backtest and paper trading runs
13. `simulation_trades` — Individual trades within simulations
14. `regime_log` — Daily market regime classifications
15. `optimize_experiments` — AutoOptimize experiment audit trail
16. `signal_attribution` — Per-signal-type performance tracking
17. `shadow_trades` — Shadow portfolio paper trades
18. `auto_check_log` — Price check audit trail
19. `baseline_scan_results` — A/B scan using frozen default params
20. `daily_scan_comparison` — Daily delta between optimized vs default scans
21. `processed_post_mortems` — Tracks which trades have been post-mortem'd by learning agent

## API Route Prefixes
- `/scanner` — Run and view scans
- `/watchlist` — CRUD + alerts
- `/calculator` — Position sizing + pyramid
- `/trades` — Trade lifecycle + stats
- `/journal` — Weekly journal CRUD
- `/market-stance` — Daily stance log
- `/alerts` — Alert management
- `/actions` — Trade action workflow
- `/simulation` — Backtest + paper trading
- `/intelligence` — Regime, CIO brief, optimization status
- `/autopilot/status` — Virtual portfolio summary
- `/autopilot/run-now` — Manual trigger scan + alert automation
- `/autopilot/comparison` — A/B parameter comparison history
- `/health` — System health + scheduler job status

## Critical Business Rules (README Section 12)
- Entry only in last 30 minutes of market session
- RPT (Risk Per Trade): 0.2%–1.0%, default 0.5%
- Max open risk: 10% of account value
- Entry split: always 50/50
- SL = Entry Price - TRP value (never moved down)
- Min TRP > 2.0 for tradeable stocks
- Min 20 bars in base formation
- Exit framework: 2R (20%), NE 4xTRP (20%), GE 8xTRP (40%), EE 12xTRP (80%)

## Position Calculator Test Cases
```
ASTERDM:   AV=500000, RPT=0.50%, Entry=601,  TRP=3.18% → Size=131, Half=65
MARICO:    AV=500000, RPT=0.50%, Entry=724.5, TRP=1.85% → Size=188, Half=94
SWARAJENG: AV=500000, RPT=0.50%, Entry=4482,  TRP=3.30% → Size=17,  Half=8
```

## Intelligence Layer (10 Scheduled Jobs)
- **exit_monitor** — SL/target checks every 2 min (9-15h IST)
- **entry_monitor** — Trigger break checks every 1 min (15:00-15:30 IST)
- **risk_guardian** — Position risk checks every 10 min (9-15h IST)
- **learning_agent** — Post-mortem on closed trades every 30 min
- **shadow_portfolio** — Shadow trade exit tracking every 30 min
- **daily_scanner** — PPC+NPC+Contraction scan at 16:00 IST
- **regime_classifier** — Market regime detection at 16:45 IST
- **cio_agent** — Daily intelligence brief at 17:00 IST
- **corpus_updater** — Market data ingestion at 17:30 IST
- **autooptimize** — Overnight parameter tuning 18:00-08:00 IST

## Autopilot System
Fully automated virtual paper trading:
- Virtual capital: 1,00,000 | RPT: 0.5% | Max risk: 10% | Max positions: 5
- Pipeline: scan -> watchlist -> BUY alert -> trade -> SELL alert -> exit
- A/B comparison: optimized params vs frozen DEFAULT_PARAMETERS daily

## Conventions
- Indian currency formatting: ₹1,00,000 (lakhs/crores)
- NSE symbols: "RELIANCE", "ASTERDM", etc.
- Decimal for all financial values (never float)
- Dates in IST, market hours 9:15 AM-3:30 PM
