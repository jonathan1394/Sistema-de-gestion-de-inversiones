"""Alembic environment configuration — resolves DB path from app config.

Falls back to the URL in alembic.ini when settings.yaml is not available.
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path
from typing import Optional

from sqlalchemy import engine_from_config, pool

from alembic import context

# Allow imports from project root
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url with the real database path from settings
# only if the caller has not already provided a custom URL.
current_url = config.get_main_option("sqlalchemy.url", "")
_DEFAULT_PLACEHOLDER = "driver://user:pass@localhost/dbname"
if not current_url or current_url == _DEFAULT_PLACEHOLDER:
    db_url: Optional[str] = None
    try:
        from app.config import load_settings  # noqa: E402

        settings = load_settings()
        db_url = f"sqlite:///{settings.database.path}"
    except Exception:
        pass
    if db_url is None:
        db_url = current_url or _DEFAULT_PLACEHOLDER
    config.set_main_option("sqlalchemy.url", db_url)

target_metadata = None


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
