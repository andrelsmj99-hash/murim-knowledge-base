"""
Application configuration using environment variables and Pydantic Settings.

The .env file is resolved relative to the project root so it works regardless
of the current working directory used to launch the process.
"""
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root: <repo>/app/utils/config.py -> parents[2] == <repo>
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # App Settings
    app_name: str = Field(default="Murim Knowledge Base", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=False, alias="APP_DEBUG")

    # Database Settings
    database_url: str = Field(
        default="postgresql://murim_user:murim_password@localhost:5432/murim_db",
        alias="DATABASE_URL",
    )

    # API Settings
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")

    # Scraping Settings
    scraper_delay_min: float = Field(default=1.0, alias="SCRAPER_DELAY_MIN")
    scraper_delay_max: float = Field(default=3.0, alias="SCRAPER_DELAY_MAX")
    max_retries: int = Field(default=5, alias="MAX_RETRIES")

    # NLP Settings
    spacy_model: str = Field(default="en_core_web_lg", alias="SPACY_MODEL")
    transformers_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        alias="TRANSFORMERS_MODEL",
    )

    # Data dirs (derived from project root)
    @property
    def data_dir(self) -> Path:
        return PROJECT_ROOT / "data"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def exports_dir(self) -> Path:
        return self.data_dir / "exports"

    @property
    def progress_dir(self) -> Path:
        return self.data_dir / "progress"

    @property
    def logs_dir(self) -> Path:
        return PROJECT_ROOT / "logs"


# Singleton instance
settings = AppConfig()
