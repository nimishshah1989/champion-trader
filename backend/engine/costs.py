"""NSE equity-delivery cost model + Indian capital-gains tax (A1).

Two layers, kept separate because they behave differently:
  * Per-transaction trading costs (brokerage, STT, exchange txn, SEBI, stamp,
    GST, DP/demat) reduce each trade's realized R.
  * Capital-gains tax (STCG/LTCG) is an annual, portfolio-level overlay applied
    to net realized gains.

All money is ``Decimal``. Default rates ≈ FY2025-26 delivery and MUST be
reconciled against a real Zerodha contract note before go-live (Phase A gate).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

_PAISE = Decimal("0.01")


def _r(x: Decimal) -> Decimal:
    """Round to paise (2 dp), half-up."""
    return x.quantize(_PAISE, rounding=ROUND_HALF_UP)


# --- Capital-gains tax (listed equity, post 23-Jul-2024) -----------------------
STCG_RATE = Decimal("0.20")        # holding <= 12 months
LTCG_RATE = Decimal("0.125")       # holding  > 12 months
LTCG_EXEMPTION = Decimal("125000")  # per financial year


@dataclass(frozen=True)
class CostModel:
    """NSE delivery (CNC) per-transaction costs. Rates are configurable."""

    brokerage_pct: Decimal = Decimal("0")          # Zerodha delivery = ₹0
    stt_pct: Decimal = Decimal("0.001")            # 0.1% each side (delivery)
    exch_txn_pct: Decimal = Decimal("0.0000297")   # NSE ≈ 0.00297%
    sebi_pct: Decimal = Decimal("0.000001")        # 0.0001% (₹10 / crore)
    stamp_pct_buy: Decimal = Decimal("0.00015")    # 0.015%, buy side only
    gst_pct: Decimal = Decimal("0.18")             # on brokerage + txn + SEBI (+ DP)
    dp_per_scrip: Decimal = Decimal("13.5")        # flat, sell side, per scrip

    def buy_costs(self, value: Decimal) -> Decimal:
        brokerage = value * self.brokerage_pct
        stt = value * self.stt_pct
        exch = value * self.exch_txn_pct
        sebi = value * self.sebi_pct
        stamp = value * self.stamp_pct_buy
        gst = self.gst_pct * (brokerage + exch + sebi)
        return _r(brokerage + stt + exch + sebi + stamp + gst)

    def sell_costs(self, value: Decimal, scrips: int = 1) -> Decimal:
        brokerage = value * self.brokerage_pct
        stt = value * self.stt_pct
        exch = value * self.exch_txn_pct
        sebi = value * self.sebi_pct
        dp = self.dp_per_scrip * Decimal(scrips)
        gst = self.gst_pct * (brokerage + exch + sebi + dp)
        return _r(brokerage + stt + exch + sebi + dp + gst)

    def round_trip_costs(
        self, buy_value: Decimal, sell_value: Decimal, scrips: int = 1
    ) -> Decimal:
        return _r(self.buy_costs(buy_value) + self.sell_costs(sell_value, scrips))


def capital_gains_tax(net_stcg: Decimal, net_ltcg: Decimal) -> Decimal:
    """Annual capital-gains tax on already-net-of-set-off realized gains.

    Taxes positive net STCG at 20% and net LTCG above the ₹1.25 L exemption at
    12.5%. Full inter-head set-off and 8-year carry-forward are the
    responsibility of the portfolio/annual layer that computes ``net_stcg`` and
    ``net_ltcg``.
    """
    stcg = max(Decimal(0), net_stcg) * STCG_RATE
    ltcg = max(Decimal(0), net_ltcg - LTCG_EXEMPTION) * LTCG_RATE
    return _r(stcg + ltcg)
