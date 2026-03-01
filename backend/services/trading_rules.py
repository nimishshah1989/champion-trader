"""
Trading rules constants from the Champion Trader methodology.
These are non-negotiable — the system enforces them as hard constraints.
Source: README.md Section 12.
"""

TRADING_RULES = {
    # Entry rules
    "entry_window_minutes_before_close": 30,
    "morning_check_delay_minutes": 15,
    "sl_monitor_delay_minutes": 10,
    "earnings_blackout_days": 3,

    # Position sizing rules
    "max_rpt_pct": 1.0,
    "min_rpt_pct": 0.2,
    "default_rpt_pct": 0.5,
    "max_open_risk_pct": 10.0,
    "entry_split": 0.5,

    # Base quality rules
    "min_base_bars": 20,
    "min_trp": 2.0,
    "min_adt_multiplier": 50,

    # Exit rules
    "mathematical_exit_r": 2,
    "mathematical_exit_pct": 0.20,
    "normal_extension_x": 4,
    "great_extension_x": 8,
    "extreme_extension_x": 12,
    "ne_exit_pct": 0.20,
    "ge_exit_pct": 0.40,
    "ee_exit_pct": 0.80,

    # Final exit
    "default_final_exit_dma": 50,
    "long_hold_final_exit_dma": 20,
    "long_hold_threshold_months": 3,

    # Volume filters
    "ppc_min_volume_ratio": 1.5,
    "ppc_min_trp_ratio": 1.5,
    "ppc_min_close_position": 0.60,

    # Market stance thresholds
    "weak_stance_tor_pct": 1.0,
    "strong_stance_tor_pct": 5.0,
}

# Telegram alert templates
ALERT_TEMPLATES = {
    "SL_HIT": "SL ALERT: {symbol} hit {sl_price}. Monitor for 10 mins. If no bounce, EXIT.",
    "TRIGGER_LEVEL": "ENTRY ALERT: {symbol} broke TL of {tl}. Ready to enter last 30 mins.",
    "PPC_DETECTED": "PPC: {symbol} showing PPC (TRP {trp_ratio}x, Vol {vol_ratio}x). Check for base.",
    "2R_HIT": "2R TARGET: {symbol} hit 2R target {target}. Consider exiting 20%.",
    "EXTENSION": "{ext_type}: {symbol} at {ext_label} ({price}). Consider partial exit.",
    "EARNINGS_WARNING": "EARNINGS: {symbol} reports in {days} days. Review exit plan.",
    "MARKET_STANCE": "Market Stance: {stance}. Suggested RPT: {rpt_pct}%. Sectors: Strong={strong}, Weak={weak}",
}
