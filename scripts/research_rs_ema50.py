"""RS EMA50x200 strategy — out-of-sample + cost validation (research only, NOT wired).

Re-implements the uploaded report's strategy from its §16 spec and stress-tests the two
things the report did NOT do:
  1. Out-of-sample: run it on 2017-2020 (the 2018 small-cap bear + 2019 narrow market +
     2020 COVID crash) — none of which the bullish 2021-2026 backtest saw.
  2. Honest frictions: add the project CostModel (NSE delivery) + slippage (report = zero).
  3. Concentration: report the top-10-trade share of gross profit and the ex-top-10 result.

Validation discipline: first REPRODUCE the report's gross 2021-2026 numbers; only then is the
OOS result trustworthy. Strategy (report §16): RS = close / NIFTY50 close; enter when RS EMA50
crosses above RS EMA200, exit on the reverse cross OR a 10% hard stop from entry. Signal at
close, fill next open, unfilled expires. Fixed Rs50,000 notional/trade, max 15, Rs10L start.
"""
import sqlite3, sys, math
import numpy as np
import pandas as pd

sys.path.insert(0, "/home/user/champion-trader")
from backend.engine.costs import CostModel
from decimal import Decimal

CACHE = "/home/user/champion-trader/champion_cache.sqlite"
START_CAP = 1_000_000.0
NOTIONAL = 50_000.0          # Capital x 0.5% / 10% stop
MAX_POS = 15
STOP_FRAC = 0.10
WARMUP = 200                 # RS bars required before a symbol may signal
WARMUP_START = "2016-04-07"  # NIFTY index history begins here
RF = 0.065
COST = CostModel()


def _costs(value, side, gross):
    if gross:
        return 0.0
    v = Decimal(str(value))
    return float(COST.buy_costs(v) if side == "buy" else COST.sell_costs(v, 1))


def universe(con, start, end, adt_cr=5.0, min_days=200):
    df = pd.read_sql(
        "SELECT symbol, AVG(close*volume)/1e7 adt, COUNT(*) n FROM bars "
        "WHERE date BETWEEN ? AND ? GROUP BY symbol", con, params=(start, end))
    return df[(df.adt >= adt_cr) & (df.n >= min_days)].symbol.tolist()


def load_signals(con, symbols, nifty, end):
    """Per symbol: a date-indexed frame with o/h/l/c + cross_up/cross_dn (post-warmup)."""
    out = {}
    ph = ",".join("?" * len(symbols))
    df = pd.read_sql(
        f"SELECT symbol,date,open,high,low,close FROM bars WHERE symbol IN ({ph}) "
        f"AND date BETWEEN ? AND ? ORDER BY symbol,date",
        con, params=symbols + [WARMUP_START, end])
    df["date"] = pd.to_datetime(df["date"])
    nf = nifty.copy()
    for sym, g in df.groupby("symbol", sort=False):
        s = g.set_index("date")[["open", "high", "low", "close"]]
        rs = (s["close"] / nf.reindex(s.index)).dropna()
        if len(rs) < WARMUP + 5:
            continue
        e50 = rs.ewm(span=50, adjust=False).mean()
        e200 = rs.ewm(span=200, adjust=False).mean()
        above = e50 > e200
        cu = above & (~above.shift(1).fillna(False))
        cd = (~above) & (above.shift(1).fillna(False))
        warm = pd.Series(np.arange(len(rs)) >= WARMUP, index=rs.index)
        s = s.assign(cu=(cu & warm).reindex(s.index, fill_value=False),
                     cd=(cd & warm).reindex(s.index, fill_value=False),
                     rs_str=(e50 / e200 - 1.0).reindex(s.index))
        out[sym] = s
    return out


def run(con, entry_start, end, gross, slip):
    nifty = pd.read_sql("SELECT date, close FROM index_bars WHERE index_code='NIFTY 50' ORDER BY date",
                        con)
    nifty["date"] = pd.to_datetime(nifty["date"]); nifty = nifty.set_index("date")["close"]
    syms = universe(con, entry_start, end)
    data = load_signals(con, syms, nifty, end)
    dates = sorted({d for s in data.values() for d in s.index if str(d.date()) >= WARMUP_START})
    entry_start = pd.Timestamp(entry_start)

    cash = START_CAP
    pos = {}                 # symbol -> dict(shares, entry, stop)
    pend_entry, pend_exit = [], []
    equity, closed = [], []  # equity curve, closed-trade P&L list

    def px(sym, d, col):
        s = data[sym]
        return float(s.at[d, col]) if d in s.index else None

    for d in dates:
        # 1. fill pending signal-exits at today's open
        for sym in pend_exit:
            if sym in pos and px(sym, d, "open") is not None:
                p = pos.pop(sym); fill = px(sym, d, "open") * (1 - slip)
                cash += fill * p["shares"] - _costs(fill * p["shares"], "sell", gross)
                closed.append((sym, (fill / p["entry"] - 1) * 100, (fill - p["entry"]) * p["shares"]))
        pend_exit = []
        # 2. fill pending entries at today's open (rank by RS strength, take free slots)
        ranked = sorted([s for s in pend_entry if s not in pos and px(s, d, "open")],
                        key=lambda s: (data[s].at[d, "rs_str"] if d in data[s].index else -9),
                        reverse=True)
        for sym in ranked:
            if len(pos) >= MAX_POS:
                break
            fill = px(sym, d, "open") * (1 + slip); shares = int(NOTIONAL // fill)
            if shares <= 0:
                continue
            cost = fill * shares + _costs(fill * shares, "buy", gross)
            if cost > cash:
                continue
            cash -= cost; pos[sym] = {"shares": shares, "entry": fill, "stop": fill * (1 - STOP_FRAC)}
        pend_entry = []
        # 3. intraday hard-stop on remaining positions (gap-aware fill)
        for sym in list(pos):
            lo = px(sym, d, "low")
            if lo is not None and lo <= pos[sym]["stop"]:
                p = pos.pop(sym); o = px(sym, d, "open")
                fill = min(o, p["stop"]) * (1 - slip)
                cash += fill * p["shares"] - _costs(fill * p["shares"], "sell", gross)
                closed.append((sym, (fill / p["entry"] - 1) * 100, (fill - p["entry"]) * p["shares"]))
        # 4. queue tomorrow's fills from today's crosses (entries only once window is open)
        if d >= entry_start:
            pend_entry = [s for s in data if d in data[s].index and bool(data[s].at[d, "cu"])]
        pend_exit = [s for s in pos if d in data[s].index and bool(data[s].at[d, "cd"])]
        # 5. mark-to-market
        mtm = sum((px(s, d, "close") or pos[s]["entry"]) * pos[s]["shares"] for s in pos)
        if d >= entry_start:
            equity.append((d, cash + mtm))

    eq = pd.Series({d: v for d, v in equity})
    return eq, closed


def metrics(eq, closed, label):
    r = eq / eq.iloc[0]
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = r.iloc[-1] ** (1 / yrs) - 1
    dd = (eq / eq.cummax() - 1).min()
    calmar = cagr / abs(dd) if dd else float("inf")
    rets = eq.pct_change().dropna()
    sharpe = (rets.mean() - RF / 252) / (rets.std() + 1e-12) * math.sqrt(252)
    pnls = [c[2] for c in closed]
    wins = [p for p in pnls if p > 0]; losses = [p for p in pnls if p <= 0]
    wr = len(wins) / len(pnls) * 100 if pnls else 0
    pf = sum(wins) / abs(sum(losses)) if losses and sum(losses) != 0 else float("inf")
    gross_profit = sum(wins)
    top10 = sum(sorted(wins, reverse=True)[:10])
    top10_share = top10 / gross_profit * 100 if gross_profit else 0
    # ex-top-10: final value if the 10 biggest winners are removed
    ex = eq.iloc[-1] - top10
    print(f"\n=== {label} ===")
    print(f"  window      {eq.index[0].date()} -> {eq.index[-1].date()}  ({yrs:.1f}y)")
    print(f"  final       Rs{eq.iloc[-1]/1e5:.2f}L  ({(r.iloc[-1]-1)*100:+.0f}%)")
    print(f"  CAGR        {cagr*100:.1f}%   maxDD {dd*100:.1f}%   Calmar {calmar:.2f}   Sharpe {sharpe:.2f}")
    print(f"  trades      {len(pnls)}   win% {wr:.0f}   PF {pf:.2f}")
    print(f"  top-10 winners = {top10_share:.0f}% of gross profit | ex-top-10 final Rs{ex/1e5:.2f}L")
    return dict(cagr=cagr, dd=dd, calmar=calmar, trades=len(pnls), final=eq.iloc[-1],
                top10_share=top10_share, ex_top10=ex)


if __name__ == "__main__":
    con = sqlite3.connect(CACHE)
    print("RS EMA50x200 validation — reproduce, then out-of-sample, then costs\n" + "=" * 64)
    # A: reproduce the report (2021-2026, GROSS = no costs/slippage)
    eqA, clA = run(con, "2021-01-01", "2026-05-31", gross=True, slip=0.0)
    metrics(eqA, clA, "A · 2021-2026 GROSS (reproduce report; report=+209%/23.7% CAGR/-24%DD/177tr)")
    # B: same window, realistic costs + slippage
    eqB, clB = run(con, "2021-01-01", "2026-05-31", gross=False, slip=0.001)
    metrics(eqB, clB, "B · 2021-2026 NET (CostModel + 10bps slippage)")
    # C: OUT-OF-SAMPLE 2017-2020, gross (pure edge test through 2018/2019/2020)
    eqC, clC = run(con, "2017-01-01", "2020-12-31", gross=True, slip=0.0)
    metrics(eqC, clC, "C · 2017-2020 OUT-OF-SAMPLE GROSS")
    # D: OOS with realistic costs
    eqD, clD = run(con, "2017-01-01", "2020-12-31", gross=False, slip=0.001)
    metrics(eqD, clD, "D · 2017-2020 OUT-OF-SAMPLE NET")
    con.close()
