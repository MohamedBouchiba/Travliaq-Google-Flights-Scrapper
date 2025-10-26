# src/core/config.py - MODIFIER pour production

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional
from pathlib import Path
import os


class Settings(BaseSettings):
    """Configuration de l'application"""

    # Environment
    environment: str = Field(default="production", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")

    # API
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_reload: bool = Field(default=False, env="API_RELOAD")

    # Scraper - Optimisé pour production
    headless: bool = Field(default=True, env="HEADLESS")
    screenshot_on_error: bool = Field(default=False, env="SCREENSHOT_ON_ERROR")  # Désactivé
    max_retries: int = Field(default=3, env="MAX_RETRIES")
    timeout: int = Field(default=30, env="TIMEOUT")

    # Anti-détection
    use_stealth: bool = Field(default=True, env="USE_STEALTH")
    random_user_agent: bool = Field(default=True, env="RANDOM_USER_AGENT")
    simulate_human: bool = Field(default=True, env="SIMULATE_HUMAN")

    # Proxy (optionnel)
    use_proxy: bool = Field(default=False, env="USE_PROXY")
    proxy_url: Optional[str] = Field(default=None, env="PROXY_URL")
    proxy_rotation: bool = Field(default=False, env="PROXY_ROTATION")

    # Database
    database_url: str = Field(
        default="sqlite:///data/flights.db",
        env="DATABASE_URL"
    )

    # Cache
    cache_ttl_minutes: int = Field(default=60, env="CACHE_TTL_MINUTES")

    # Logs - Minimaux en production
    log_level: str = Field(default="WARNING", env="LOG_LEVEL")  # WARNING = peu de logs
    log_file: str = Field(default="logs/scraper.log", env="LOG_FILE")
    log_rotation_size: int = Field(default=10, env="LOG_ROTATION_MB")  # 10MB max
    log_retention_days: int = Field(default=3, env="LOG_RETENTION_DAYS")  # 3 jours

    # Rate Limiting
    requests_per_hour: int = Field(default=30, env="REQUESTS_PER_HOUR")
    delay_between_requests_min: float = Field(default=3.0, env="DELAY_BETWEEN_REQUESTS_MIN")
    delay_between_requests_max: float = Field(default=7.0, env="DELAY_BETWEEN_REQUESTS_MAX")

    # Sentry
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")
    sentry_environment: str = Field(default="production", env="SENTRY_ENVIRONMENT")
    sentry_traces_sample_rate: float = Field(default=0.1, env="SENTRY_TRACES_SAMPLE_RATE")

    # Paths
    @property
    def base_dir(self) -> Path:
        return Path(__file__).parent.parent.parent

    @property
    def data_dir(self) -> Path:
        return self.base_dir / "data"

    @property
    def logs_dir(self) -> Path:
        return self.base_dir / "logs"

    def ensure_directories(self):
        """Crée les répertoires nécessaires"""
        directories = [
            self.data_dir,
            self.logs_dir,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
settings.ensure_directories()

# Constantes
PROJECT_NAME = "Travliaq Google Flights Scraper"
API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"