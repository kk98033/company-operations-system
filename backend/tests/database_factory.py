"""Database resource test doubles shared by focused unit tests."""

from __future__ import annotations

from unittest.mock import Mock

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import DatabaseResources


def make_database_resources(
    *,
    engine: Engine | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> DatabaseResources:
    """Return isolated resources that never open a real connection."""

    return DatabaseResources(
        engine=engine or Mock(spec=Engine),
        session_factory=session_factory or Mock(spec=sessionmaker),
    )
