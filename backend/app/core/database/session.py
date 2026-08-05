"""Request-scoped SQLAlchemy session dependency."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session


def get_database_session(request: Request) -> Iterator[Session]:
    """Yield one session and always close it without auto-committing."""

    session = request.app.state.database.session_factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
