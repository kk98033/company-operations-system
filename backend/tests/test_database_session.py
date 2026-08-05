"""Unit tests for request-scoped session cleanup."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from app.core.database.session import get_database_session


def _request_with_session(session: Session) -> SimpleNamespace:
    session_factory = Mock(return_value=session)
    database = SimpleNamespace(session_factory=session_factory)
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(database=database)))


def test_database_session_closes_without_implicit_commit() -> None:
    session = Mock(spec=Session)
    dependency = get_database_session(_request_with_session(session))

    assert next(dependency) is session

    with pytest.raises(StopIteration):
        next(dependency)

    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_called_once_with()


def test_database_session_rolls_back_exception_and_always_closes() -> None:
    session = Mock(spec=Session)
    dependency = get_database_session(_request_with_session(session))
    next(dependency)

    with pytest.raises(RuntimeError, match="transaction failed"):
        dependency.throw(RuntimeError("transaction failed"))

    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()
    session.close.assert_called_once_with()
