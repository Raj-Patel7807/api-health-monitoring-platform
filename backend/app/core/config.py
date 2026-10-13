from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables, with safe local defaults."""

    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/api_health"
    redis_url: str = "redis://localhost:6379/0"
    llm_enabled: bool = False

    # Base64url-encoded 32-byte AES-256 key. Generate: python -m app.core.crypto
    # No default on purpose: a shared default key would defeat the encryption.
    encryption_key: str = ""

    # JWT settings (US-01 — Sprint 2)
    # Generate a secret: python -c "import secrets; print(secrets.token_hex(32))"
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
