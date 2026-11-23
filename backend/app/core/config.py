from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables, with safe local defaults."""

    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/api_health"
    redis_url: str = "redis://localhost:6379/0"
    # Email sender configuration
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@example.com"
    # Webhook configuration
    webhook_secret: str = ""
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
    def celery_redis_url(self) -> str:
        """Upstash TCP endpoints require TLS for the broker and result backend."""
        url = urlsplit(self.redis_url)
        host = (url.hostname or "").rstrip(".")
        if url.scheme not in {"redis", "rediss"} or not host.endswith(".upstash.io"):
            return self.redis_url

        options = [
            (name, value)
            for name, value in parse_qsl(url.query, keep_blank_values=True)
            if name != "ssl_cert_reqs"
        ]
        options.append(("ssl_cert_reqs", "required"))
        return url._replace(scheme="rediss", query=urlencode(options)).geturl()

    def signing_key(self) -> str:
        from app.core.crypto import EncryptionConfigError

        key = self.jwt_secret_key.strip()
        if len(key) < 32:
            raise EncryptionConfigError("JWT_SECRET_KEY must be at least 32 characters.")
        if key == self.encryption_key.strip():
            raise EncryptionConfigError("JWT_SECRET_KEY must be independent of ENCRYPTION_KEY.")
        return self.jwt_secret_key

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
