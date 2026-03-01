from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    text,
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
    created_at = Column(String, server_default="CURRENT_TIMESTAMP")


# --- Table 2: scan_results ---
class ScanResult(Base):
    __tablename__ = "scan_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_date = Column(Date, nullable=False)
    symbol = Column(String, nullable=False)
    scan_type = Column(String, nullable=False)  # PPC, NPC, CONTRACTION

    # Price data at time of scan
    close_price = Column(Float)
    volume = Column(Integer)
    avg_volume_20d = Column(Float)
    volume_ratio = Column(Float)

    # TRP data
    trp = Column(Float)
    avg_trp = Column(Float)
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
    adt = Column(Float)
    passes_liquidity_filter = Column(Boolean)

    # Wake-up call type
    wuc_type = Column(String)  # MBB, BA, EF, GU, EG, NULL

    # Categorisation
    watchlist_bucket = Column(String)  # READY, NEAR, AWAY
    trigger_level = Column(Float)

    notes = Column(Text)
    created_at = Column(String, server_default="CURRENT_TIMESTAMP")


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
    trigger_level = Column(Float)
    planned_entry_price = Column(Float)

    # Position planning
    planned_sl_pct = Column(Float)
    planned_position_size = Column(Integer)
    planned_half_qty = Column(Integer)

    # Status tracking
    status = Column(String, default="ACTIVE")  # ACTIVE, TRADED, REMOVED, EXPIRED
    removed_reason = Column(Text)

    notes = Column(Text)
    last_updated = Column(String, server_default="CURRENT_TIMESTAMP")
    created_at = Column(String, server_default="CURRENT_TIMESTAMP")


# --- Table 4: trades ---
class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, nullable=False)

    # Entry details
    entry_date = Column(Date, nullable=False)
    entry_type = Column(String)  # LIVE_BREAK, CLOSE_ABOVE, NEXT_DAY_HIGH
    entry_price_half1 = Column(Float)
    entry_price_half2 = Column(Float)
    qty_half1 = Column(Integer)
    qty_half2 = Column(Integer)
    total_qty = Column(Integer)
    avg_entry_price = Column(Float)

    # Risk parameters at entry
    trp_at_entry = Column(Float)
    sl_price = Column(Float)
    sl_pct = Column(Float)
    rpt_amount = Column(Float)

    # Target levels
    target_2r = Column(Float)
    target_ne = Column(Float)
    target_ge = Column(Float)
    target_ee = Column(Float)

    # Exit tracking
    exit_date = Column(Date)
    exit_method = Column(String)
    exit_price = Column(Float)
    exit_qty = Column(Integer)

    # P&L
    gross_pnl = Column(Float)
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

    created_at = Column(String, server_default="CURRENT_TIMESTAMP")
    updated_at = Column(String, server_default="CURRENT_TIMESTAMP")


# --- Table 5: partial_exits ---
class PartialExit(Base):
    __tablename__ = "partial_exits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=False)
    exit_date = Column(Date, nullable=False)
    exit_price = Column(Float, nullable=False)
    exit_qty = Column(Integer, nullable=False)
    exit_reason = Column(String)  # 2R, NE, GE, EE, EARNINGS_RISK, MANUAL
    r_multiple_at_exit = Column(Float)
    pnl = Column(Float)
    notes = Column(Text)
    created_at = Column(String, server_default="CURRENT_TIMESTAMP")


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
    created_at = Column(String, server_default="CURRENT_TIMESTAMP")


# --- Table 7: weekly_journal ---
class WeeklyJournal(Base):
    __tablename__ = "weekly_journal"

    id = Column(Integer, primary_key=True, autoincrement=True)
    week_start = Column(Date, nullable=False, unique=True)
    week_end = Column(Date, nullable=False)

    # Account performance
    account_value_start = Column(Float)
    account_value_end = Column(Float)
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

    created_at = Column(String, server_default="CURRENT_TIMESTAMP")
    updated_at = Column(String, server_default="CURRENT_TIMESTAMP")


# --- Table 8: position_calc_sessions ---
class PositionCalcSession(Base):
    __tablename__ = "position_calc_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    calc_date = Column(Date, nullable=False)
    symbol = Column(String, nullable=False)

    account_value = Column(Float, nullable=False)
    rpt_pct = Column(Float, nullable=False)
    rpt_amount = Column(Float, nullable=False)

    entry_price = Column(Float, nullable=False)
    sl_pct = Column(Float, nullable=False)
    sl_amount = Column(Float, nullable=False)
    sl_price = Column(Float, nullable=False)

    position_value = Column(Float, nullable=False)
    position_size = Column(Integer, nullable=False)
    half_qty = Column(Integer, nullable=False)

    # Pre-calculated targets
    target_2r = Column(Float)
    target_ne = Column(Float)
    target_ge = Column(Float)
    target_ee = Column(Float)

    notes = Column(Text)
    created_at = Column(String, server_default="CURRENT_TIMESTAMP")


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
    created_at = Column(String, server_default=text("(datetime('now'))"))


def init_db() -> None:
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for FastAPI routes — yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
