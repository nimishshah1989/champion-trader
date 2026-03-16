from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    create_engine,
    func,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.config import settings

# Use check_same_thread=False for SQLite with FastAPI
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# --- Table 1: stocks ---
class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, nullable=False, unique=True)
    company_name = Column(String)
    sector = Column(String)
    industry = Column(String)
    exchange = Column(String, default="NSE")
    is_active = Column(Boolean, default=True)
    created_at = Column(String, server_default=func.now())


# --- Table 2: scan_results ---
class ScanResult(Base):
    __tablename__ = "scan_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_date = Column(Date, nullable=False)
    symbol = Column(String, nullable=False)
    scan_type = Column(String, nullable=False)  # PPC, NPC, CONTRACTION

    # Price data at time of scan
    close_price = Column(Numeric(15, 2))
    volume = Column(Integer)
    avg_volume_20d = Column(Float)
    volume_ratio = Column(Float)

    # TRP data
    trp = Column(Numeric(15, 2))
    avg_trp = Column(Numeric(15, 2))
    trp_ratio = Column(Float)

    # Candle characteristics
    candle_body_pct = Column(Float)
    close_position = Column(Float)

    # Stage analysis
    stage = Column(String)  # S1, S1B, S2, S3, S4
    above_30w_ma = Column(Boolean)
    ma_trending_up = Column(Boolean)

    # Base analysis
    base_days = Column(Integer)
    has_min_20_bar_base = Column(Boolean)
    base_quality = Column(String)  # SMOOTH, CHOPPY, MIXED

    # Liquidity
    adt = Column(Numeric(15, 2))
    passes_liquidity_filter = Column(Boolean)

    # Wake-up call type
    wuc_type = Column(String)  # MBB, BA, EF, GU, EG, NULL

    # Categorisation
    watchlist_bucket = Column(String)  # READY, NEAR, AWAY
    trigger_level = Column(Numeric(15, 2))

    notes = Column(Text)
    created_at = Column(String, server_default=func.now())


# --- Table 3: watchlist ---
class Watchlist(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, nullable=False)
    added_date = Column(Date, nullable=False)
    bucket = Column(String, nullable=False)  # READY, NEAR, AWAY

    # Analysis snapshot
    stage = Column(String)
    base_days = Column(Integer)
    base_quality = Column(String)
    wuc_types = Column(String)  # comma-separated

    # Entry parameters (for READY stocks)
    trigger_level = Column(Numeric(15, 2))
    planned_entry_price = Column(Numeric(15, 2))

    # Position planning
    planned_sl_pct = Column(Float)
    planned_position_size = Column(Integer)
    planned_half_qty = Column(Integer)

    # Status tracking
    status = Column(String, default="ACTIVE")  # ACTIVE, TRADED, REMOVED, EXPIRED
    removed_reason = Column(Text)

    notes = Column(Text)
    last_updated = Column(String, server_default=func.now())
    created_at = Column(String, server_default=func.now())


# --- Table 4: trades ---
class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, nullable=False)

    # Entry details
    entry_date = Column(Date, nullable=False)
    entry_type = Column(String)  # LIVE_BREAK, CLOSE_ABOVE, NEXT_DAY_HIGH
    entry_price_half1 = Column(Numeric(15, 2))
    entry_price_half2 = Column(Numeric(15, 2))
    qty_half1 = Column(Integer)
    qty_half2 = Column(Integer)
    total_qty = Column(Integer)
    avg_entry_price = Column(Numeric(15, 2))

    # Risk parameters at entry
    trp_at_entry = Column(Numeric(15, 2))
    sl_price = Column(Numeric(15, 2))
    sl_pct = Column(Float)
    rpt_amount = Column(Numeric(15, 2))

    # Target levels
    target_2r = Column(Numeric(15, 2))
    target_ne = Column(Numeric(15, 2))
    target_ge = Column(Numeric(15, 2))
    target_ee = Column(Numeric(15, 2))

    # Exit tracking
    exit_date = Column(Date)
    exit_method = Column(String)
    exit_price = Column(Numeric(15, 2))
    exit_qty = Column(Integer)

    # P&L
    gross_pnl = Column(Numeric(15, 2))
    r_multiple = Column(Float)
    pnl_pct = Column(Float)

    # Trade status
    status = Column(String, default="OPEN")  # OPEN, PARTIAL, CLOSED
    remaining_qty = Column(Integer)

    # Context
    market_stance_at_entry = Column(String)
    setup_type = Column(String)
    entry_notes = Column(Text)
    exit_notes = Column(Text)

    created_at = Column(String, server_default=func.now())
    updated_at = Column(String, server_default=func.now())


# --- Table 5: partial_exits ---
class PartialExit(Base):
    __tablename__ = "partial_exits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=False)
    exit_date = Column(Date, nullable=False)
    exit_price = Column(Numeric(15, 2), nullable=False)
    exit_qty = Column(Integer, nullable=False)
    exit_reason = Column(String)  # 2R, NE, GE, EE, EARNINGS_RISK, MANUAL
    r_multiple_at_exit = Column(Float)
    pnl = Column(Numeric(15, 2))
    notes = Column(Text)
    created_at = Column(String, server_default=func.now())


# --- Table 6: market_stance_log ---
class MarketStanceLog(Base):
    __tablename__ = "market_stance_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    log_date = Column(Date, nullable=False, unique=True)

    # Sector strength
    strong_sectors = Column(Text)  # comma-separated
    weak_sectors = Column(Text)  # comma-separated

    # Derived
    strong_count = Column(Integer)
    weak_count = Column(Integer)
    stance = Column(String)  # WEAK, MODERATE, STRONG

    # Adjustments
    rpt_pct = Column(Float)
    max_positions = Column(Integer)

    notes = Column(Text)
    created_at = Column(String, server_default=func.now())


# --- Table 7: weekly_journal ---
class WeeklyJournal(Base):
    __tablename__ = "weekly_journal"

    id = Column(Integer, primary_key=True, autoincrement=True)
    week_start = Column(Date, nullable=False, unique=True)
    week_end = Column(Date, nullable=False)

    # Account performance
    account_value_start = Column(Numeric(15, 2))
    account_value_end = Column(Numeric(15, 2))
    weekly_return_pct = Column(Float)

    # Expectancy metrics
    trades_taken = Column(Integer)
    win_count = Column(Integer)
    loss_count = Column(Integer)
    win_rate = Column(Float)
    avg_win_r = Column(Float)
    avg_loss_r = Column(Float)
    arr = Column(Float)

    # Grave mistakes
    grave_casual_trade = Column(Boolean, default=False)
    grave_sl_violation = Column(Boolean, default=False)
    grave_risk_exceeded = Column(Boolean, default=False)
    grave_averaged_down = Column(Boolean, default=False)
    grave_rebought_loser = Column(Boolean, default=False)

    # Risk management review
    rm_winrate_arr_eval = Column(Text)
    rm_market_stance_accuracy = Column(Text)
    rm_rpt_consistency = Column(Text)
    rm_or_matrix_violated = Column(Boolean, default=False)
    rm_slippage_issues = Column(Text)
    rm_streak_handling = Column(Text)

    # Technical review
    tech_random_trades = Column(Text)
    tech_poor_setups = Column(Text)
    tech_entry_timing = Column(Text)
    tech_sl_placement = Column(Text)
    tech_exit_framework = Column(Text)
    tech_extension_judgment = Column(Text)
    tech_earnings_handling = Column(Text)

    # Routine adherence
    routine_scans_daily = Column(Boolean, default=True)
    routine_watchlist_updated = Column(Boolean, default=True)
    routine_setup_tracker_updated = Column(Boolean, default=True)
    routine_screen_time_minimised = Column(Boolean, default=True)
    routine_historical_analysis = Column(Text)

    # Psychology
    psych_affirmations_read = Column(Boolean, default=True)
    psych_impulsive_actions = Column(Text)
    psych_fear_greed_influence = Column(Text)
    psych_social_trading_influence = Column(Boolean, default=False)
    psych_stress_level = Column(String)  # LOW, MEDIUM, HIGH

    # Summary
    excelled_at = Column(Text)
    poor_at = Column(Text)
    key_learnings = Column(Text)

    created_at = Column(String, server_default=func.now())
    updated_at = Column(String, server_default=func.now())


# --- Table 8: position_calc_sessions ---
class PositionCalcSession(Base):
    __tablename__ = "position_calc_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    calc_date = Column(Date, nullable=False)
    symbol = Column(String, nullable=False)

    account_value = Column(Numeric(15, 2), nullable=False)
    rpt_pct = Column(Float, nullable=False)
    rpt_amount = Column(Numeric(15, 2), nullable=False)

    entry_price = Column(Numeric(15, 2), nullable=False)
    sl_pct = Column(Float, nullable=False)
    sl_amount = Column(Numeric(15, 2), nullable=False)
    sl_price = Column(Numeric(15, 2), nullable=False)

    position_value = Column(Numeric(15, 2), nullable=False)
    position_size = Column(Integer, nullable=False)
    half_qty = Column(Integer, nullable=False)

    # Pre-calculated targets
    target_2r = Column(Numeric(15, 2))
    target_ne = Column(Numeric(15, 2))
    target_ge = Column(Numeric(15, 2))
    target_ee = Column(Numeric(15, 2))

    notes = Column(Text)
    created_at = Column(String, server_default=func.now())


# --- Table 10: app_alerts ---
class AppAlert(Base):
    __tablename__ = "app_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_type = Column(String, nullable=False)  # SL_HIT, TRIGGER_LEVEL, PPC_DETECTED, NPC_DETECTED, 2R_HIT, EXTENSION, EARNINGS_WARNING, MARKET_STANCE, SYSTEM
    symbol = Column(String)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String, default="info")  # info, warning, critical
    is_read = Column(Boolean, default=False)
    data = Column(Text)  # JSON string with extra data
    created_at = Column(String, server_default=func.now())


# --- Table 11: action_alerts ---
class ActionAlert(Base):
    __tablename__ = "action_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_category = Column(String, nullable=False)  # BUY, SELL
    alert_type = Column(String, nullable=False)  # TRIGGER_BREAK, SL_HIT, 2R_HIT, NE_HIT, GE_HIT, EE_HIT, FINAL_EXIT
    symbol = Column(String, nullable=False)
    current_price = Column(Numeric(15, 2))
    trigger_price = Column(Numeric(15, 2))

    # BUY-specific fields
    suggested_qty = Column(Integer)
    suggested_half_qty = Column(Integer)
    suggested_sl_price = Column(Numeric(15, 2))
    suggested_entry_price = Column(Numeric(15, 2))
    account_value_used = Column(Numeric(15, 2))
    rpt_pct_used = Column(Float)
    trp_pct = Column(Float)

    # SELL-specific fields
    trade_id = Column(Integer, ForeignKey("trades.id"))
    exit_qty = Column(Integer)
    exit_pct = Column(Float)
    target_level = Column(Numeric(15, 2))
    remaining_qty_after = Column(Integer)

    action_text = Column(Text)  # Human-readable instruction
    status = Column(String, default="NEW")  # NEW, ACTED, DISMISSED, EXPIRED
    acted_at = Column(DateTime)

    resulting_trade_id = Column(Integer, ForeignKey("trades.id"))
    resulting_partial_exit_id = Column(Integer, ForeignKey("partial_exits.id"))

    source = Column(String, default="PRICE_CHECK")  # PRICE_CHECK, WEBHOOK
    watchlist_id = Column(Integer, ForeignKey("watchlist.id"))
    data = Column(Text)  # JSON string with extra data
    created_at = Column(String, server_default=func.now())


# --- Table 12: simulation_runs ---
class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_type = Column(String, nullable=False)  # BACKTEST, PAPER
    name = Column(String)
    starting_capital = Column(Numeric(15, 2), nullable=False)
    rpt_pct = Column(Float, nullable=False)
    start_date = Column(Date)
    end_date = Column(Date)  # null for PAPER until stopped

    # Status: PENDING/RUNNING/COMPLETED/FAILED for BACKTEST; ACTIVE/PAUSED/STOPPED for PAPER
    status = Column(String, default="PENDING")

    # Summary results
    final_capital = Column(Numeric(15, 2))
    total_pnl = Column(Numeric(15, 2))
    total_return_pct = Column(Float)
    total_trades = Column(Integer, default=0)
    win_count = Column(Integer, default=0)
    loss_count = Column(Integer, default=0)
    win_rate = Column(Float)
    avg_win_r = Column(Float)
    avg_loss_r = Column(Float)
    arr = Column(Float)
    expectancy = Column(Float)
    max_drawdown_pct = Column(Float)
    max_drawdown_amount = Column(Numeric(15, 2))

    equity_curve = Column(Text)  # JSON text: [{date, equity}]
    last_processed_date = Column(Date)  # for PAPER
    error_message = Column(Text)
    created_at = Column(String, server_default=func.now())
    updated_at = Column(String, server_default=func.now())


# --- Table 13: simulation_trades ---
class SimulationTrade(Base):
    __tablename__ = "simulation_trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("simulation_runs.id"), nullable=False)
    symbol = Column(String, nullable=False)
    signal_date = Column(Date)
    entry_date = Column(Date)
    entry_price = Column(Numeric(15, 2))
    total_qty = Column(Integer)
    half_qty = Column(Integer)
    trp_pct = Column(Float)
    sl_price = Column(Numeric(15, 2))
    rpt_amount = Column(Numeric(15, 2))
    target_2r = Column(Numeric(15, 2))
    target_ne = Column(Numeric(15, 2))
    target_ge = Column(Numeric(15, 2))
    target_ee = Column(Numeric(15, 2))

    # Exit tracking — qty exited at each target level
    qty_exited_2r = Column(Integer, default=0)
    qty_exited_ne = Column(Integer, default=0)
    qty_exited_ge = Column(Integer, default=0)
    qty_exited_ee = Column(Integer, default=0)
    qty_exited_sl = Column(Integer, default=0)
    qty_exited_final = Column(Integer, default=0)
    remaining_qty = Column(Integer)

    status = Column(String, default="OPEN")  # OPEN, PARTIAL, CLOSED
    exit_date = Column(Date)
    gross_pnl = Column(Numeric(15, 2))
    r_multiple = Column(Float)
    pnl_pct = Column(Float)
    portfolio_value_at_entry = Column(Numeric(15, 2))
    created_at = Column(String, server_default=func.now())


# --- Intelligence Layer Tables ---


# --- Table 14: regime_log ---
class RegimeLog(Base):
    __tablename__ = "regime_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    regime_date = Column(Date, nullable=False, unique=True)
    regime = Column(String(20), nullable=False)  # TRENDING_BULL, RANGING_QUIET, HIGH_VOLATILITY, WEAKENING_BEAR
    nifty_adx = Column(Float)
    india_vix = Column(Float)
    fii_net_crore = Column(Numeric(15, 2))
    hurst_exponent = Column(Float)
    nifty_close = Column(Numeric(15, 2))
    nifty_sma150 = Column(Numeric(15, 2))
    param_bank_version = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())


# --- Table 15: optimize_experiments ---
class OptimizeExperiment(Base):
    __tablename__ = "optimize_experiments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_date = Column(Date, nullable=False)
    parameter_name = Column(String(100), nullable=False)
    old_value = Column(Float, nullable=False)
    new_value = Column(Float, nullable=False)
    hypothesis = Column(Text)
    old_score = Column(Float)
    new_score = Column(Float)
    outcome = Column(String(10))  # KEEP or REVERT
    trade_count = Column(Integer)
    expectancy = Column(Float)
    max_drawdown_pct = Column(Float)
    created_at = Column(DateTime, server_default=func.now())


# --- Table 16: signal_attribution ---
class SignalAttribution(Base):
    __tablename__ = "signal_attribution"

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_type = Column(String(20), nullable=False)
    regime = Column(String(20), nullable=False)
    param_bank_version = Column(String(50))
    trade_count = Column(Integer, default=0)
    win_count = Column(Integer, default=0)
    total_r = Column(Float, default=0.0)
    avg_r = Column(Float)
    win_rate = Column(Float)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# --- Table 17: shadow_trades ---
class ShadowTrade(Base):
    __tablename__ = "shadow_trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_date = Column(Date, nullable=False)
    symbol = Column(String(20), nullable=False)
    signal_type = Column(String(20), nullable=False)
    composite_score = Column(Float)
    entry_price = Column(Numeric(15, 2))
    stop_price = Column(Numeric(15, 2))
    target_price = Column(Numeric(15, 2))
    rr_ratio = Column(Float)
    regime = Column(String(20))
    was_approved = Column(Boolean, default=False)
    paper_exit_price = Column(Numeric(15, 2))
    paper_exit_date = Column(Date)
    paper_pnl = Column(Numeric(15, 2))
    paper_r_multiple = Column(Float)
    created_at = Column(DateTime, server_default=func.now())


# --- Table 18: auto_check_log ---
class AutoCheckLog(Base):
    """Audit trail for every automated and manual price check."""

    __tablename__ = "auto_check_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(20), nullable=False, default="MANUAL")  # MANUAL | SCHEDULER
    check_type = Column(String(20), nullable=False, default="FULL")  # FULL | EXITS | ENTRIES
    symbols_checked = Column(Integer, default=0)
    prices_fetched = Column(Integer, default=0)
    buy_alerts_new = Column(Integer, default=0)   # net-new alerts created this run
    sell_alerts_new = Column(Integer, default=0)
    duration_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


def init_db() -> None:
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for FastAPI routes -- yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
