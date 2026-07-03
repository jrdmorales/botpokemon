from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://pokeprecio:pokeprecio@192.168.1.100:5432/pokeprecio"

    # Scraping
    stores_config_dir: Path = Path(__file__).resolve().parent.parent / "stores"
    scrape_full_interval_hours: int = 6
    scrape_preorder_interval_hours: int = 1
    request_delay_min_s: float = 2.0
    request_delay_max_s: float = 5.0
    max_retries: int = 3
    user_agent: str = (
        "PokePrecioBot/0.1 (monitor de precios; contacto: sbjordansb@gmail.com)"
    )
    # Tras N scrapes consecutivos sin ver un listing se marca descontinuado
    missing_scrapes_before_discontinued: int = 4

    # Matching
    fuzzy_auto_match_threshold: int = 92
    fuzzy_review_threshold: int = 85

    # Alertas
    deal_alert_min_discount_pct: float = 20.0
    historic_min_required_days: int = 14
    deal_baseline_days: int = 30

    # Frescura de datos: listings con scrape más viejo se atenúan/excluyen
    stale_data_hours: int = 12

    # Telegram
    telegram_bot_token: str = ""
    telegram_admin_chat_id: str = ""

    # API
    admin_api_key: str = "change-me"


@lru_cache
def get_settings() -> Settings:
    return Settings()
