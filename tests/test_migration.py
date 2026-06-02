"""Tests for the additive v2 trail/attribution migration — additive & idempotent."""
import importlib.util
import pathlib
import sqlite3

_PATH = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "migrate_add_v2_trail_columns.py"
_spec = importlib.util.spec_from_file_location("migrate_v2", _PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
migrate, COLUMNS = _mod.migrate, _mod.COLUMNS

TRADES_NEW = {"current_stop", "highest_high", "atr_at_entry", "signal_type",
              "regime_at_entry", "volume_ratio_at_entry", "avg_trp_at_entry", "strategy_version"}
SIM_NEW = {"current_stop", "highest_high", "atr_at_entry"}


def _old_schema_db(path):
    """A DB as it existed BEFORE this migration (no trail columns)."""
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE trades (id INTEGER PRIMARY KEY, symbol TEXT, sl_price NUMERIC)")
    con.execute("CREATE TABLE simulation_trades (id INTEGER PRIMARY KEY, symbol TEXT)")
    con.commit()
    con.close()


def _cols(path, table):
    con = sqlite3.connect(path)
    try:
        return {r[1] for r in con.execute(f"PRAGMA table_info({table})")}
    finally:
        con.close()


def test_migration_adds_all_v2_columns(tmp_path):
    db = str(tmp_path / "old.db")
    _old_schema_db(db)
    added, _ = migrate(db)
    assert added == len(COLUMNS)
    assert TRADES_NEW <= _cols(db, "trades")
    assert SIM_NEW <= _cols(db, "simulation_trades")


def test_migration_is_idempotent(tmp_path):
    db = str(tmp_path / "old.db")
    _old_schema_db(db)
    migrate(db)
    added2, skipped2 = migrate(db)        # second run is a no-op
    assert added2 == 0 and skipped2 == len(COLUMNS)


def test_strategy_version_defaults_to_v2(tmp_path):
    db = str(tmp_path / "old.db")
    _old_schema_db(db)
    migrate(db)
    con = sqlite3.connect(db)
    con.execute("INSERT INTO trades (symbol) VALUES ('X')")
    con.commit()
    val = con.execute("SELECT strategy_version FROM trades WHERE symbol='X'").fetchone()[0]
    con.close()
    assert val == "v2"
