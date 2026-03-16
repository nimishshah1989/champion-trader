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

    # TradingView Webhook
    webhook_secret: str = ""

    # CORS
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # App settings
    app_port: int = 8000
    environment: str = "development"

    # Defaults
    default_account_value: Decimal = Decimal("1000000")
    default_rpt_pct: float = 0.50
    default_exchange: str = "NSE"

    # Anthropic (CIO Agent + AutoOptimize)
    anthropic_api_key: str = ""

    # AutoOptimize
    autooptimize_enabled: bool = True
    autooptimize_start_hour: int = 18
    autooptimize_halt_hour: int = 8
    autooptimize_model: str = "claude-sonnet-4-5"

    # RAG
    rag_persist_dir: str = "./rag/chromadb"
    corpus_b_retention_days: int = 90

    # Broker
    broker_live_trading: bool = False
    broker_type: str = "paper"  # paper | jhaveri

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
