import pytest

from app.core.config import Settings
from app.db.session import create_database_engine


def test_cors_origins_are_split_and_trimmed() -> None:
    settings = Settings(cors_origins="http://one.test, http://two.test ")

    assert settings.cors_origin_list == ["http://one.test", "http://two.test"]


@pytest.mark.parametrize("scheme", ["redis", "rediss"])
def test_upstash_uses_verified_tls_and_preserves_connection_details(scheme: str) -> None:
    endpoint = "default:p%40ss%2Fword@queue.upstash.io:6379/0"
    settings = Settings(redis_url=f"{scheme}://{endpoint}?socket_timeout=8&ssl_cert_reqs=none")
    assert (
        settings.celery_redis_url == f"rediss://{endpoint}?socket_timeout=8&ssl_cert_reqs=required"
    )


def test_upstash_tcp_url_without_a_query_enables_tls() -> None:
    settings = Settings(redis_url="redis://default:fixture@queue.upstash.io:6379")
    assert settings.celery_redis_url == (
        "rediss://default:fixture@queue.upstash.io:6379?ssl_cert_reqs=required"
    )


@pytest.mark.parametrize(
    "url", ["redis://redis:6379/0", "rediss://other.example/1?ssl_cert_reqs=required"]
)
def test_other_redis_endpoints_keep_their_configured_transport(url: str) -> None:
    assert Settings(redis_url=url).celery_redis_url == url


def test_database_engine_uses_configured_postgres_url() -> None:
    engine = create_database_engine()

    assert engine.dialect.name == "postgresql"
    engine.dispose()


@pytest.mark.parametrize("key", ["", "short", "x" * 32])
def test_startup_rejects_invalid_signing_key(monkeypatch, key):
    from app.auth.tokens import create_access_token
    from app.core.config import get_settings
    from app.core.crypto import EncryptionConfigError

    monkeypatch.setenv("ENCRYPTION_KEY", "x" * 32)
    monkeypatch.setenv("JWT_SECRET_KEY", key)
    get_settings.cache_clear()
    try:
        with pytest.raises(EncryptionConfigError, match="JWT_SECRET_KEY"):
            create_access_token({"sub": "test"})
    finally:
        get_settings.cache_clear()
