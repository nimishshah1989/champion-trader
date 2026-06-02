"""Additive migration: v2 trailing-stop + attribution columns (Phase 0, REWIRE_PLAN §5).

The validated v2 stop MOVES (5xATR chandelier). The live `trades` table only had a
static, write-once `sl_price` — so a trailing exit could not be represented at all
(REWIRE_PLAN's "#1 blocker"). This adds the trail + attribution columns to `trades` and
the trail trio to `simulation_trades`.

`Base.metadata.create_all` creates missing *tables* but never adds *columns* to an
existing table, so this ALTERs in place. Idempotent and additive — it only adds columns
that are missing, never drops or rewrites data. Safe to run repeatedly.

    python scripts/migrate_add_v2_trail_columns.py [sqlite_path]
"""
import sqlite3
import sys

# (table, column, sqlite_type) — types mirror the SQLAlchemy models in backend/tables.py
COLUMNS = [
    ("trades", "current_stop", "NUMERIC"),
    ("trades", "highest_high", "NUMERIC"),
    ("trades", "atr_at_entry", "NUMERIC"),
    ("trades", "signal_type", "TEXT"),
    ("trades", "regime_at_entry", "TEXT"),
    ("trades", "volume_ratio_at_entry", "NUMERIC"),
    ("trades", "avg_trp_at_entry", "NUMERIC"),
    ("trades", "strategy_version", "TEXT DEFAULT 'v2'"),
    ("simulation_trades", "current_stop", "NUMERIC"),
    ("simulation_trades", "highest_high", "NUMERIC"),
    ("simulation_trades", "atr_at_entry", "NUMERIC"),
]


def _sqlite_path(url: str) -> str:
    if not url.startswith("sqlite"):
        raise SystemExit(f"This migration only supports SQLite; got {url!r}")
    return url.split("sqlite:///", 1)[-1] if "sqlite:///" in url else url.split("sqlite://", 1)[-1]


def _existing_columns(con: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in con.execute(f"PRAGMA table_info({table})")}


def migrate(path: str) -> tuple[int, int]:
    con = sqlite3.connect(path)
    added = skipped = 0
    try:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table, col, sqltype in COLUMNS:
            if table not in tables:
                print(f"  - {table}.{col}: table absent (created fresh with the column) — skip")
                skipped += 1
                continue
            if col in _existing_columns(con, table):
                print(f"  = {table}.{col}: already present — skip")
                skipped += 1
                continue
            con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {sqltype}")
            print(f"  + {table}.{col} {sqltype}")
            added += 1
        con.commit()
    finally:
        con.close()
    return added, skipped


if __name__ == "__main__":
    # backend (SQLAlchemy/pydantic) is only needed by the CLI entrypoint, not by migrate()
    sys.path.insert(0, "/home/user/champion-trader")
    from backend.config import settings   # noqa: E402
    from backend.database import init_db   # noqa: E402

    init_db()   # ensure tables exist (fresh DBs get the columns from the models directly)
    path = sys.argv[1] if len(sys.argv) > 1 else _sqlite_path(settings.database_url)
    print(f"Migrating {path} ...")
    added, skipped = migrate(path)
    print(f"\nDone: {added} column(s) added, {skipped} already present/created fresh.")
