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

## Database Tables (8 total)
1. `stocks` — Stock master data (NSE symbols)
2. `scan_results` — Daily PPC/NPC/Contraction scan outputs
3. `watchlist` — READY/NEAR/AWAY categorised stocks
4. `trades` — Full trade lifecycle with partial exits
5. `partial_exits` — Individual partial exit records per trade
6. `market_stance_log` — Daily sector strength assessment
7. `weekly_journal` — Weekly self-review (Champion Journal format)
8. `position_calc_sessions` — Saved position sizing calculations

## API Route Prefixes
- `/scanner` — Run and view scans
- `/watchlist` — CRUD + alerts
- `/calculator` — Position sizing + pyramid
- `/trades` — Trade lifecycle + stats
- `/journal` — Weekly journal CRUD
- `/market-stance` — Daily stance log
- `/webhook` — TradingView + Dhan incoming alerts

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

## Build Phases
1. Core Engine (Position Calculator) — current
2. Watchlist + Market Stance
3. Trade Log + Journal
4. Pine Scripts
5. Automation (webhooks + Telegram)
6. Broker Integration (Dhan)

## Conventions
- Indian currency formatting: ₹1,00,000 (lakhs/crores)
- NSE symbols: "RELIANCE", "ASTERDM", etc.
- All monetary values stored as floats (not paisa — this is a trading tool, not payments)
- Dates in IST, market hours 9:15 AM–3:30 PM
