from app.core.config import Settings
from app.db.session import create_database_engine


def test_cors_origins_are_split_and_trimmed() -> None:
    settings = Settings(cors_origins="http://one.test, http://two.test ")

    assert settings.cors_origin_list == ["http://one.test", "http://two.test"]


def test_database_engine_uses_configured_postgres_url() -> None:
    engine = create_database_engine()

    assert engine.dialect.name == "postgresql"
    engine.dispose()
