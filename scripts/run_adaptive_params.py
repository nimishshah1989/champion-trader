"""Adaptive parameter study — first-principles, no new parameters.

Two hypotheses:
  A) Regime speed: our 150-SMA + 20-bar slope is deliberately slow. A faster
     regime signal (50-bar slope test, or shorter SMA) responds sooner to
     market turns. Test faster vs slower regime detection.

  B) Regime-adaptive chandelier: in a STRONG bull trend (price well above SMA),
     let winners ride longer (mult=5). In a WEAK bull (barely above SMA), trail
     tighter (mult=2). This is not a new parameter — we're using the EXISTING
     regime state differently. Same logic Afzal uses: the market IS the context.

Neither adds complexity. Both use the same data already computed.
"""
import sys
import time
import sqlite3
from datetime import date
from decimal import Decimal

sys.path.insert(0, "/home/user/champion-trader")
from backend.engine.backtest_fast import run_universe_backtest  # noqa: E402
from backend.engine.regime import load_regime  # noqa: E402

CACHE = "/home/user/champion-trader/champion_cache.sqlite"
START = date(2016, 4, 7)


# ── A: Regime speed sweep ────────────────────────────────────────────────────
# Load regime with different SMA window + slope lookback, count how many
# trading days are "regime on" and the transition lag after a bull market top.
print("A. REGIME SPEED ANALYSIS\n")
print(f"{'SMA':>5}{'slope_lb':>9}{'days_on':>9}{'on%':>6}  description")
import sqlite3 as _sq, pandas as pd, numpy as np
from datetime import date as _date

con = _sq.connect(CACHE)
rows = con.execute("select date,close from index_bars where index_code='NIFTY 500' order by date").fetchall()
con.close()
df = pd.DataFrame(rows, columns=["date","close"])
df["date"] = pd.to_datetime(df["date"])
df["close"] = df["close"].astype(float)

for sma_w, slope_lb in [(50,5),(100,10),(150,20),(200,30)]:
    sma = df["close"].rolling(sma_w).mean()
    on = (df["close"] > sma) & (sma > sma.shift(slope_lb))
    n_on = on.sum()
    pct = n_on / len(on)
    # avg lag to re-enter after a trough (days from SMA cross to regime-on)
    print(f"{sma_w:>5}{slope_lb:>9}{n_on:>9}{pct:>6.0%}  {'CURRENT' if sma_w==150 else ''}")

# show 2022 bear / 2023 recovery lags
print("\n  2022 bear start / 2023 recovery — regime-on dates:")
for sma_w, slope_lb in [(50,5),(100,10),(150,20)]:
    sma = df["close"].rolling(sma_w).mean()
    on = (df["close"] > sma) & (sma > sma.shift(slope_lb))
    on_dates = df["date"][on].dt.date.tolist()
    # first off date in 2022
    off_dates = df["date"][~on].dt.date.tolist()
    d2022_off = next((d for d in off_dates if d >= _date(2022,1,1)), None)
    d2023_on  = next((d for d in on_dates if d >= _date(2022,6,1)), None)
    lag = (d2023_on - d2022_off).days if d2023_on and d2022_off else "?"
    print(f"  SMA{sma_w}/slope{slope_lb}: regime-off {d2022_off}  back-on {d2023_on}  lag={lag}d")


# ── B: Regime-adaptive chandelier mult backtest ───────────────────────────────
print("\n\nB. REGIME-ADAPTIVE CHANDELIER MULT\n")
print("Idea: mult = f(price vs SMA) — strong trend gets wider trail.")
print("Not a new param — uses the same SMA already computed in regime filter.\n")
print(f"{'config':32}{'trades':>7}{'win':>7}{'avgWinR':>9}{'avgLossR':>9}{'expR':>8}{'SQN':>7}{'finalEq':>13}")

# Test fixed vs adaptive using run_universe_backtest with different mult values
# Proxy for adaptive: we can't inject per-bar mult into run_universe_backtest without
# refactoring. Instead, test the two extremes + current to understand sensitivity,
# then implement the adaptive version in backtest_fast.py.
for label, kw in [
    ("chandelier 2x +regime (weak-trend proxy)", dict(exit_mode="chandelier", chandelier_mult=2.0, use_regime=True)),
    ("chandelier 3x +regime (current)",          dict(exit_mode="chandelier", chandelier_mult=3.0, use_regime=True)),
    ("chandelier 5x +regime (strong-trend proxy)",dict(exit_mode="chandelier", chandelier_mult=5.0, use_regime=True)),
    ("chandelier 2x +regime +52w (tighter)",     dict(exit_mode="chandelier", chandelier_mult=2.0, use_regime=True, use_52w=True, max_pct_52w=15.0)),
    ("chandelier 5x +regime +52w (wider)",       dict(exit_mode="chandelier", chandelier_mult=5.0, use_regime=True, use_52w=True, max_pct_52w=15.0)),
]:
    t = time.time()
    res, _ = run_universe_backtest(CACHE, start_date=START, **kw)
    rs = res.r_multiples
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    aw = sum(wins)/len(wins) if wins else 0
    al = sum(losses)/len(losses) if losses else 0
    print(f"{label:32}{res.num_trades:>7}{res.win_rate:>7.1%}{aw:>9.2f}{al:>9.2f}"
          f"{res.expectancy:>+8.3f}{res.sqn:>7.2f}{res.final_equity:>13,.0f}  ({time.time()-t:.0f}s)")


# ── C: Regime speed vs edge ───────────────────────────────────────────────────
print("\n\nC. FASTER REGIME DETECTION — does being more responsive to market turns help?\n")
print(f"{'sma_w':>6}{'slope_lb':>9}{'trades':>7}{'win':>7}{'expR':>8}{'SQN':>7}{'finalEq':>13}")

# Monkey-patch regime params via direct load_regime calls + manual run
from backend.engine.backtest_fast import _fast_simulate, load_bars
from backend.engine.precompute import precompute_features
from backend.engine.backtest import replay_trades, RawTrade

def run_with_regime_params(sma_w, slope_lb):
    regime_map, _ = load_regime(CACHE, "NIFTY 500", sma_window=sma_w, slope_lb=slope_lb)
    con2 = sqlite3.connect(CACHE)
    symbols = [r[0] for r in con2.execute("select symbol from done where n>0 order by symbol")]
    raw = []
    for s in symbols:
        bs = load_bars(con2, s)
        if len(bs) < 200:
            continue
        df2 = precompute_features(bs)
        raw += _fast_simulate(s, bs, df2, exit_mode="chandelier", target_r=2.0,
                              chandelier_mult=3.0, slippage=Decimal("0.001"), min_trp=2.0,
                              start_date=START, use_regime=True, regime_map=regime_map)
    con2.close()
    return replay_trades(raw, starting_capital=Decimal("1000000"), rpt_pct=0.5)

for sma_w, slope_lb in [(50,5),(100,10),(150,20),(200,30)]:
    t = time.time()
    res = run_with_regime_params(sma_w, slope_lb)
    tag = " ← CURRENT" if sma_w == 150 else ""
    print(f"{sma_w:>6}{slope_lb:>9}{res.num_trades:>7}{res.win_rate:>7.1%}"
          f"{res.expectancy:>+8.3f}{res.sqn:>7.2f}{res.final_equity:>13,.0f}  ({time.time()-t:.0f}s){tag}")
