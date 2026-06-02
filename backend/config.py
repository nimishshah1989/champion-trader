from decimal import Decimal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from .env file."""

    # Database
    database_url: str = "sqlite:///./champion_trader.db"

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Dhan Broker API
    dhan_client_id: str = ""
    dhan_access_token: str = ""

    # Zerodha Kite Connect
    kite_api_key: str = ""
    kite_api_secret: str = ""
    kite_access_token: str = ""

    # TradingView Webhook
    webhook_secret: str = ""

    # CORS
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # App settings
    app_port: int = 8000
    environment: str = "development"

    # Bar store (Kite-adjusted daily OHLCV) — the SAME feed the backtest reads, so the
    # live v2 scan/entry/exit are parity-faithful. Path to the sqlite written by the Kite
    # ingest (scripts/ingest_kite_daily.py). The legacy yfinance scan feed is retired.
    bars_db_path: str = "./champion_cache.sqlite"

    # Paper engine — virtual account the validated v2 strategy trades until go-live.
    # ₹10,00,000 over the full universe (≥ liquidity floor): non-degenerate sizing for the
    # paper run (₹1L rounds expensive names to 0 shares). Tune per the fill reconciliation.
    paper_capital: Decimal = Decimal("1000000")

    # Defaults
    default_account_value: Decimal = Decimal("1000000")
    default_rpt_pct: Decimal = Decimal("0.50")
    default_exchange: str = "NSE"

    # Anthropic (CIO Agent + AutoOptimize)
    anthropic_api_key: str = ""

    # AutoOptimize — FROZEN for the v2 rollout: the StrategyParams/RiskParams are validated
    # and parity-gated, so overnight auto-tuning must NOT perturb them. Re-enable only to
    # research a *new* versioned config against the validated backtester (never the live one).
    autooptimize_enabled: bool = False
    autooptimize_start_hour: int = 18
    autooptimize_halt_hour: int = 8
    autooptimize_model: str = "claude-sonnet-4-5"

    # RAG
    rag_persist_dir: str = "./rag/chromadb"
    corpus_b_retention_days: int = 90

    # Broker
    broker_live_trading: bool = False
    broker_type: str = "paper"  # paper | jhaveri

    # extra="ignore": the .env also carries keys the research layer uses (SUPABASE_*,
    # Atlas) that this model doesn't declare — the app must not crash on them.
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
