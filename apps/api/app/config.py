"""Application settings loaded from environment (PH_* prefix)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    Override via environment variables (e.g. ``PH_DATABASE_URL=...``) or a ``.env`` file.
    """

    model_config = SettingsConfigDict(env_prefix="PH_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./persona_hub.db"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    handoff_token_ttl_seconds: int = 300
    rate_limit_default: str = "100/minute"
    enable_rate_limit: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
