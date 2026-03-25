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
)

# Use check_same_thread=False for SQLite with FastAPI
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
