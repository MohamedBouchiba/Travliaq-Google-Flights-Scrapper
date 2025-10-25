"""
Configuration centralisée pour Travliaq Google Flights Scraper
Utilise pydantic-settings pour valider et charger les variables d'environnement
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional
from pathlib import Path
import os


class Settings(BaseSettings):
    """Configuration de l'application"""
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    
    # API
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_reload: bool = Field(default=True, env="API_RELOAD")
    
    # Scraper
    headless: bool = Field(default=False, env="HEADLESS")
    screenshot_on_error: bool = Field(default=True, env="SCREENSHOT_ON_ERROR")
    max_retries: int = Field(default=3, env="MAX_RETRIES")
    timeout: int = Field(default=25, env="TIMEOUT")
    
    # Proxy
    use_proxy: bool = Field(default=False, env="USE_PROXY")
    proxy_url: Optional[str] = Field(default=None, env="PROXY_URL")
    
    # Database
    database_url: str = Field(
        default="sqlite:///data/flights.db",
        env="DATABASE_URL"
    )
    
    # Cache
    cache_ttl_minutes: int = Field(default=60, env="CACHE_TTL_MINUTES")  # 1 heure par défaut
    
    # Logs
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="logs/scraper.log", env="LOG_FILE")
    
    # Rate Limiting
    requests_per_hour: int = Field(default=50, env="REQUESTS_PER_HOUR")
    delay_between_requests_min: float = Field(default=2.0, env="DELAY_BETWEEN_REQUESTS_MIN")
    delay_between_requests_max: float = Field(default=5.0, env="DELAY_BETWEEN_REQUESTS_MAX")
    
    # Paths
    @property
    def base_dir(self) -> Path:
        """Répertoire racine du projet"""
        return Path(__file__).parent.parent.parent
    
    @property
    def data_dir(self) -> Path:
        """Répertoire des données"""
        return self.base_dir / "data"
    
    @property
    def logs_dir(self) -> Path:
        """Répertoire des logs"""
        return self.base_dir / "logs"
    
    @property
    def screenshots_dir(self) -> Path:
        """Répertoire des screenshots"""
        return self.base_dir / "screenshots"
    
    @property
    def exports_dir(self) -> Path:
        """Répertoire des exports"""
        return self.data_dir / "exports"
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Valide le niveau de log"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level doit être parmi {valid_levels}")
        return v.upper()
    
    @validator("cache_ttl_minutes")
    def validate_cache_ttl(cls, v):
        """Valide le TTL du cache"""
        if v < 0:
            raise ValueError("cache_ttl_minutes doit être positif")
        return v
    
    def ensure_directories(self):
        """Crée les répertoires nécessaires s'ils n'existent pas"""
        directories = [
            self.data_dir,
            self.data_dir / "raw",
            self.data_dir / "processed",
            self.exports_dir,
            self.logs_dir,
            self.screenshots_dir,
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Instance globale des settings
settings = Settings()

# Créer les répertoires au démarrage
settings.ensure_directories()


# Configuration pour différents environnements
class DevelopmentSettings(Settings):
    """Configuration pour le développement"""
    environment: str = "development"
    debug: bool = True
    headless: bool = False
    log_level: str = "DEBUG"


class ProductionSettings(Settings):
    """Configuration pour la production"""
    environment: str = "production"
    debug: bool = False
    headless: bool = True
    log_level: str = "INFO"
    api_reload: bool = False


class TestingSettings(Settings):
    """Configuration pour les tests"""
    environment: str = "testing"
    debug: bool = True
    database_url: str = "sqlite:///data/test_flights.db"
    headless: bool = True
    log_level: str = "DEBUG"


def get_settings() -> Settings:
    """
    Factory pour obtenir les settings selon l'environnement
    Utile pour l'injection de dépendances FastAPI
    """
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionSettings()
    elif env == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()


# Export des constantes utiles
PROJECT_NAME = "Travliaq Google Flights Scraper"
API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"