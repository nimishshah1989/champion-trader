# Champion Trader — Paper-Live Runbook

How to run the validated v2 strategy in **paper mode** on live Kite data. No real orders are
placed (`broker_live_trading=False`); the Kite broker client is a kill-switched Phase-2 stub.

> Architecture: `ARCHITECTURE.md` · Build status: `REWIRE_PLAN.md` (Phase 1 complete).

---

## 1. One-time setup

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python scripts/migrate_add_v2_trail_columns.py     # additive trail/attribution columns
```

**`.env`** (copy from `.env.example` if present):

| Key | Needed for | Notes |
| :-- | :-- | :-- |
| `KITE_API_KEY`, `KITE_API_SECRET` | bar ingest | Kite Connect app with **Historical Data (daily candles)** access. That is the ONLY Kite feature the paper run uses — no live quotes, no order API. Verify the current plan/price on the Kite Connect site; any tier that includes the historical daily-candle API is sufficient for the entire paper phase. The order API is needed only in Phase 2 (real money). |
| `KITE_ACCESS_TOKEN` | bar ingest | **expires daily** — refreshed by step 3 each morning |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | alerts (optional) | without them, fills just log |
| `BROKER_LIVE_TRADING` | — | leave `false` (paper). The kill-switch for Phase 2. |

Config defaults already set for the run: **`paper_capital=₹10,00,000`**, full universe ≥ ₹5cr/day
liquidity floor, RPT 0.35%, max 15 positions, AutoOptimize frozen.

## 2. Initial bar-store backfill (once)

Pulls Kite's adjusted daily history into `champion_cache.sqlite` (the feed the backtest used).
Needs a valid access token first (step 3).

```bash
python scripts/ingest_kite_daily.py --start 2015-01-01     # ~1,270 symbols + 2 indices
```

## 3. Daily Kite login (every market morning — the one manual step)

Zerodha access tokens expire ~6 AM IST and require an interactive login:

```bash
python scripts/kite_login.py                       # prints the login URL
# open it, log in -> redirected to <redirect>?request_token=XXXX&status=success
python scripts/kite_login.py --request-token XXXX  # writes KITE_ACCESS_TOKEN into .env
```

## 4. Run the app (scheduler must stay alive, IST timezone)

```bash
uvicorn backend.main:app --port 8000               # keep running; host clock/TZ = IST
```

The scheduler then runs the **post-close v2 loop** automatically:

| Time (IST) | Job | Action |
| :-- | :-- | :-- |
| 17:30 | `kite_ingest` | refresh bars + indices (no-op if Kite unconfigured) |
| 17:40 | `exit_monitor` | close-based 5×ATR chandelier stop on open trades |
| 17:45 | `entry_monitor` | open breakouts of READY names, risk-sized |
| 17:50 | `daily_scanner` | v2 SETUP scan → watchlist triggers for tomorrow |
| 09:15 | `morning_gap` | exit any position that gaps open below its stop |

`risk_guardian` (every 10 min, market hours) tracks the 15%/7.5% drawdown breaker.

## 5. Watch it

- `GET /health` — scheduler status + next run time per job.
- `GET /autopilot/status` — virtual portfolio P&L.
- Telegram — entry/exit fills (if configured).
- DB: `trades` (with `current_stop`/`highest_high`/attribution), `scan_results` (V2 rows),
  `action_alerts`.

## 6. Manual trigger (testing, any time)

```python
from backend.services import live_jobs
live_jobs.run_daily_ingest()          # refresh store
live_jobs.run_exit_pass()             # close-based exits on the latest bar
live_jobs.run_entry_pass()            # breakout entries from the READY watchlist
live_jobs.run_daily_scan()            # rebuild the watchlist
```

## 7. The gate before real money (do NOT skip)

1. **10–15 clean paper sessions.** Reconcile paper fills vs the backtest — especially thin
   names (the +178R backtest winner was an illiquid micro-cap that may not fill at size).
2. Paper Calmar / maxDD / win-rate within the backtest's band (26.5% CAGR / 14.8% DD / 1.79).
3. **Only then:** implement the `KiteBrokerClient` order methods, contract-note cost check,
   set `BROKER_LIVE_TRADING=true` + `BROKER_TYPE=kite`, start on reduced RPT / small capital,
   with the kill-switch drilled. (Phase 2 — see `REWIRE_PLAN.md` §Phase 2.)

## Parity gates (must stay green on any engine change)

```bash
python scripts/run_runtime_parity.py 0      # per-symbol: 293/293, 0 mismatches
python scripts/run_portfolio_parity.py      # portfolio: 0/2503, 26.5/14.8/1.79
```
