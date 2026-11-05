from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    database_url: str = "sqlite:///./chamaledger.db"
    environment: str = "local"
    service_version: str = "dev"
    cors_origins: str = ""
    otel_enabled: bool = False
    otel_endpoint: str = "http://otel-collector:4318"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
