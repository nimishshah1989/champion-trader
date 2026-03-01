from datetime import date
from typing import Optional

from pydantic import BaseModel


class JournalCreate(BaseModel):
    week_start: date
    week_end: date
    account_value_start: Optional[float] = None
    account_value_end: Optional[float] = None

    # Grave mistakes
    grave_casual_trade: bool = False
    grave_sl_violation: bool = False
    grave_risk_exceeded: bool = False
    grave_averaged_down: bool = False
    grave_rebought_loser: bool = False

    # Risk management
    rm_winrate_arr_eval: Optional[str] = None
    rm_market_stance_accuracy: Optional[str] = None
    rm_rpt_consistency: Optional[str] = None
    rm_or_matrix_violated: bool = False
    rm_slippage_issues: Optional[str] = None
    rm_streak_handling: Optional[str] = None

    # Technical
    tech_random_trades: Optional[str] = None
    tech_poor_setups: Optional[str] = None
    tech_entry_timing: Optional[str] = None
    tech_sl_placement: Optional[str] = None
    tech_exit_framework: Optional[str] = None
    tech_extension_judgment: Optional[str] = None
    tech_earnings_handling: Optional[str] = None

    # Routine
    routine_scans_daily: bool = True
    routine_watchlist_updated: bool = True
    routine_setup_tracker_updated: bool = True
    routine_screen_time_minimised: bool = True
    routine_historical_analysis: Optional[str] = None

    # Psychology
    psych_affirmations_read: bool = True
    psych_impulsive_actions: Optional[str] = None
    psych_fear_greed_influence: Optional[str] = None
    psych_social_trading_influence: bool = False
    psych_stress_level: Optional[str] = None  # LOW, MEDIUM, HIGH

    # Summary
    excelled_at: Optional[str] = None
    poor_at: Optional[str] = None
    key_learnings: Optional[str] = None


class JournalUpdate(BaseModel):
    """All fields optional for partial updates."""

    account_value_end: Optional[float] = None
    grave_casual_trade: Optional[bool] = None
    grave_sl_violation: Optional[bool] = None
    grave_risk_exceeded: Optional[bool] = None
    grave_averaged_down: Optional[bool] = None
    grave_rebought_loser: Optional[bool] = None
    rm_winrate_arr_eval: Optional[str] = None
    rm_market_stance_accuracy: Optional[str] = None
    rm_rpt_consistency: Optional[str] = None
    rm_or_matrix_violated: Optional[bool] = None
    rm_slippage_issues: Optional[str] = None
    rm_streak_handling: Optional[str] = None
    tech_random_trades: Optional[str] = None
    tech_poor_setups: Optional[str] = None
    tech_entry_timing: Optional[str] = None
    tech_sl_placement: Optional[str] = None
    tech_exit_framework: Optional[str] = None
    tech_extension_judgment: Optional[str] = None
    tech_earnings_handling: Optional[str] = None
    routine_scans_daily: Optional[bool] = None
    routine_watchlist_updated: Optional[bool] = None
    routine_setup_tracker_updated: Optional[bool] = None
    routine_screen_time_minimised: Optional[bool] = None
    routine_historical_analysis: Optional[str] = None
    psych_affirmations_read: Optional[bool] = None
    psych_impulsive_actions: Optional[str] = None
    psych_fear_greed_influence: Optional[str] = None
    psych_social_trading_influence: Optional[bool] = None
    psych_stress_level: Optional[str] = None
    excelled_at: Optional[str] = None
    poor_at: Optional[str] = None
    key_learnings: Optional[str] = None


class JournalResponse(BaseModel):
    id: int
    week_start: date
    week_end: date
    account_value_start: Optional[float] = None
    account_value_end: Optional[float] = None
    weekly_return_pct: Optional[float] = None
    trades_taken: Optional[int] = None
    win_count: Optional[int] = None
    loss_count: Optional[int] = None
    win_rate: Optional[float] = None
    arr: Optional[float] = None
    excelled_at: Optional[str] = None
    poor_at: Optional[str] = None
    key_learnings: Optional[str] = None

    model_config = {"from_attributes": True}
