from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "GitHub Sentinel AI"
    environment: str = "development"
    host: str = "127.0.0.1"
    port: int = 8000
    database_path: str = "./data/sentinel.db"
    github_webhook_secret: str = ""
    max_webhook_bytes: int = Field(default=1_048_576, ge=1_024, le=10_485_760)
    integration_token: str = Field(default="", validation_alias="SENTINEL_INTEGRATION_TOKEN")
    ai_enabled: bool = False
    ai_base_url: str = ""
    ai_api_key: str = ""
    ai_model: str = ""
    ai_timeout_seconds: float = 20.0
    log_level: str = "INFO"

    @property
    def database_file(self) -> Path:
        return Path(self.database_path)


@lru_cache
def get_settings() -> Settings:
    return Settings()
