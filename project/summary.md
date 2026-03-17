# Champion Trader System — Session Summary

**Date:** 2026-03-17
**State:** Fully automated autopilot + A/B comparison system deployed and live

---

## What's Live on Production

### Infrastructure
- **Backend:** champion-api.jslwealth.in (port 8003, Docker)
- **Frontend:** champion.jslwealth.in (port 3003, Docker)
- **Server:** 13.206.34.214 (t3.large, Mumbai)
- **DB:** SQLite at /app/db_data/champion_trader.db (20 tables)

### 10 Scheduled Jobs (APScheduler, IST)
| Job | Schedule | Status |
|-----|----------|--------|
| exit_monitor | Every 2 min, Mon-Fri 9-15h | Running |
| entry_monitor | Every 1 min, Mon-Fri 15:00-15:30 | Running |
| risk_guardian | Every 10 min, Mon-Fri 9-15h | Running |
| learning_agent | Every 30 min, Mon-Fri 9-16h | Running |
| shadow_portfolio | :15, :45, Mon-Fri 9-16h | Running |
| daily_scanner | Mon-Fri 16:00 | Running |
| regime_classifier | Mon-Fri 16:45 | Running |
| cio_agent | Mon-Fri 17:00 | Running |
| corpus_updater | Mon-Fri 17:30 | Running |
| autooptimize | Mon-Fri 18:00 (runs until 08:00) | Running |

### Autopilot Pipeline (Fully Automated)
1. **16:00** — Daily scanner runs PPC+NPC+Contraction on ~500 stocks
2. **16:00** — Baseline scanner runs same scans with frozen DEFAULT_PARAMETERS
3. **16:00** — A/B comparison computed and stored in daily_scan_comparison table
4. **16:00** — Autopilot auto-populates watchlist (READY/NEAR stocks)
5. **15:00-15:30** — Entry monitor checks READY watchlist for trigger breaks
6. **15:00-15:30** — Autopilot auto-executes BUY alerts as virtual trades
7. **9:00-15:30** — Exit monitor checks open trades for SL/target hits
8. **9:00-15:30** — Autopilot auto-executes SELL alerts
9. **18:00-08:00** — AutoOptimize runs overnight experiments via Claude API

### Risk Guardrails (Hardcoded, Never Overridden)
- Virtual Capital: 1,00,000
- RPT: 0.5% per trade
- Max Open Risk: 10% of capital (10,000)
- Max Positions: 5 simultaneous
- Min TRP: 2.0% (below = untradeable)

### A/B Comparison System
- `DEFAULT_PARAMETERS` frozen as of 2026-03-17 (human-defined baseline)
- `PARAMETERS` modified nightly by AutoOptimize
- Daily comparison tracks: overlap, optimizer-only, baseline-only stocks
- API: GET /autopilot/comparison?days=30

### Current Data (2026-03-17)
- Scanner: 7 PPC signals (TATACONSUM, ATUL, SYNGENE, LTTS, ESABINDIA, etc.)
- Watchlist: 1 active (HATSUN in READY)
- Trades: 0 open (waiting for entry window 15:00-15:30)
- Virtual P&L: 0

---

## Recent Changes (This Session)

### Backend
- **baseline_scanner.py** (NEW) — A/B scan with frozen params
- **autopilot.py** (NEW) — Automated paper trading engine
- **autopilot_report.py** (NEW) — Virtual portfolio summary
- **database.py** — Added BaselineScanResult + DailyScanComparison tables
- **strategy.py** — Added DEFAULT_PARAMETERS frozen dict
- **scanner_engine.py** — run_all_scans returns (results, data) tuple
- **main.py** — Wired baseline scanner, autopilot, comparison endpoint
- **middleware/decimal_fix.py** — Fixed Content-Length mismatch bug

### Frontend
- **info-tooltip.tsx** — Fixed broken Radix tooltip triggers on pipeline cards

### Endpoints Added
- GET /autopilot/status — Virtual portfolio + open trades
- POST /autopilot/run-now — Manual trigger for scan + alert automation
- GET /autopilot/comparison — A/B parameter comparison history

---

## Known Issues
- Comparison data will only populate after 16:00 IST scan runs
- AutoOptimize first experiment runs tonight at 18:00 IST
- No trades yet — first opportunity at 15:00-15:30 if HATSUN triggers

## Next Steps
- Monitor first full automated day cycle (scan → watchlist → entry → exit)
- Review first AutoOptimize experiment results tomorrow
- Review A/B comparison data after first baseline scan
- Consider adding Telegram notifications for trade executions
