"""Alembic runtime wired to validated application settings."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection

from app.core.config import load_settings
from app.core.database import Base
from app.core.database.model_registry import REGISTERED_MODELS
from app.core.database.resources import create_database_resources

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
assert REGISTERED_MODELS


def run_migrations_with_connection(connection: Connection) -> None:
    """Configure and execute migrations on one established connection."""

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_offline() -> None:
    """Render SQL without establishing a database connection."""

    settings = load_settings()
    context.configure(
        url=settings.database_url_value(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations using the same guarded engine policy as the API."""

    resources = create_database_resources(load_settings())
    try:
        with resources.engine.connect() as connection:
            run_migrations_with_connection(connection)
    finally:
        resources.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
