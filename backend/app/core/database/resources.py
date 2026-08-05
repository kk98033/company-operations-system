"""Construction and disposal of process-level database resources."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import AppSettings


@dataclass(frozen=True, slots=True)
class DatabaseResources:
    """One engine and session factory owned by an application instance."""

    engine: Engine
    session_factory: sessionmaker[Session]

    def dispose(self) -> None:
        """Release all pooled connections during application shutdown."""

        self.engine.dispose()


def create_database_resources(settings: AppSettings) -> DatabaseResources:
    """Create lazy SQLAlchemy resources from the validated secret DSN."""

    engine = create_engine(
        settings.database_url_value(),
        connect_args={"connect_timeout": 5},
        echo=False,
        hide_parameters=True,
        pool_pre_ping=True,
        pool_recycle=1_800,
        pool_size=5,
        max_overflow=2,
        pool_timeout=5,
    )
    return DatabaseResources(
        engine=engine,
        session_factory=sessionmaker(
            bind=engine,
            autoflush=False,
            expire_on_commit=False,
        ),
    )
