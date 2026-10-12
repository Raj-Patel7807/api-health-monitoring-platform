import os
import socket
import subprocess
from logging.config import fileConfig
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

from alembic import context

# ---------------------------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------------------------
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent
root_dir = backend_dir.parent

load_dotenv(backend_dir / ".env")
load_dotenv(root_dir / ".env")

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# target_metadata is None for raw SQL migrations (no autogenerate)
target_metadata = None


def get_database_url() -> str:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")
        host = os.getenv("POSTGRES_HOST", "127.0.0.1")
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "api_health_db")
        db_url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"

    # Auto-resolve host if localhost/127.0.0.1 is not reachable (WSL2 bridge)
    try:
        # Standardize scheme for parsing
        scheme_prefix = ""
        parseable_url = db_url
        if "+psycopg" in parseable_url:
            parseable_url = parseable_url.replace("+psycopg", "")
            scheme_prefix = "+psycopg"

        parsed = urlparse(parseable_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 5432

        if host in ("localhost", "127.0.0.1"):
            reachable = False
            try:
                with socket.create_connection((host, port), timeout=0.5):
                    reachable = True
            except (TimeoutError, OSError):
                reachable = False

            if not reachable:
                try:
                    res = subprocess.run(
                        ["wsl", "-d", "Ubuntu-24.04", "--", "hostname", "-I"],
                        capture_output=True,
                        text=True,
                        timeout=2,
                    )
                    if res.returncode == 0 and res.stdout.strip():
                        wsl_ip = res.stdout.strip().split()[0]
                        with socket.create_connection((wsl_ip, port), timeout=0.5):
                            new_netloc = parsed.netloc.replace(f"@{host}", f"@{wsl_ip}").replace(
                                host, wsl_ip
                            )
                            parsed = parsed._replace(netloc=new_netloc)
                            parseable_url = urlunparse(parsed)
                except Exception:
                    pass

        db_url = parseable_url
        if scheme_prefix and not db_url.startswith(f"postgresql{scheme_prefix}"):
            db_url = db_url.replace("postgresql://", f"postgresql{scheme_prefix}://", 1)
    except Exception:
        pass

    # Normalize url driver for SQLAlchemy + psycopg v3
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

    return db_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
