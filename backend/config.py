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

    # App settings
    app_port: int = 8000
    environment: str = "development"

    # Defaults
    default_account_value: float = 1000000
    default_rpt_pct: float = 0.50
    default_exchange: str = "NSE"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
