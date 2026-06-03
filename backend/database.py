"""
Database engine, session, and table re-exports.

All table classes are defined in backend.tables and re-exported here
so that existing imports like `from backend.database import Trade` continue to work.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.config import settings

# Re-export Base and all 20 table classes from tables.py
from backend.tables import (  # noqa: F401
    Base,
    Stock,
    ScanResult,
    Watchlist,
    Trade,
    PartialExit,
    MarketStanceLog,
    WeeklyJournal,
    PositionCalcSession,
    AppAlert,
    ActionAlert,
    SimulationRun,
    SimulationTrade,
    RegimeLog,
    OptimizeExperiment,
    SignalAttribution,
    ShadowTrade,
    AutoCheckLog,
    BaselineScanResult,
    DailyScanComparison,
    ProcessedPostMortem,
)

# Use check_same_thread=False for SQLite with FastAPI
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create all tables in the database, then add any missing columns."""
    Base.metadata.create_all(bind=engine)
    _migrate_columns()


def _migrate_columns() -> None:
    """Add columns that were added to models after the initial schema was deployed."""
    migrations = [
        # v2 trailing-stop columns added to `trades`
        ("trades", "current_stop",             "NUMERIC(15, 2)"),
        ("trades", "highest_high",             "NUMERIC(15, 2)"),
        ("trades", "atr_at_entry",             "NUMERIC(15, 4)"),
        ("trades", "signal_type",              "TEXT"),
        ("trades", "regime_at_entry",          "TEXT"),
        ("trades", "volume_ratio_at_entry",    "NUMERIC(10, 4)"),
        ("trades", "avg_trp_at_entry",         "NUMERIC(10, 4)"),
        ("trades", "strategy_version",         "TEXT DEFAULT 'v2'"),
        # Paper parity columns for `simulation_trades`
        ("simulation_trades", "current_stop",             "NUMERIC(15, 2)"),
        ("simulation_trades", "highest_high",             "NUMERIC(15, 2)"),
        ("simulation_trades", "atr_at_entry",             "NUMERIC(15, 4)"),
    ]
    with engine.connect() as conn:
        for table, col, col_type in migrations:
            existing = [
                row[1]
                for row in conn.execute(
                    __import__("sqlalchemy").text(f"PRAGMA table_info({table})")
                )
            ]
            if col not in existing:
                conn.execute(
                    __import__("sqlalchemy").text(
                        f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"
                    )
                )
                conn.commit()


def get_db():
    """Dependency for FastAPI routes -- yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
