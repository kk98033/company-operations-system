"""Unit tests for the real SQL database readiness contract."""

from unittest.mock import MagicMock, Mock

from sqlalchemy import Engine
from sqlalchemy.exc import OperationalError

from app.core.database import DatabaseReadinessCheck


def _engine_returning(value: object) -> tuple[Engine, MagicMock]:
    connection = MagicMock()
    connection.scalar.return_value = value
    connection_context = MagicMock()
    connection_context.__enter__.return_value = connection
    engine = Mock(spec=Engine)
    engine.connect.return_value = connection_context
    return engine, connection_context


def test_database_readiness_executes_select_one_and_closes_connection() -> None:
    engine, connection_context = _engine_returning(1)

    result = DatabaseReadinessCheck(engine)()

    assert result.model_dump() == {
        "name": "database",
        "status": "ok",
        "message": None,
    }
    scalar_call = connection_context.__enter__.return_value.scalar.call_args
    assert str(scalar_call.args[0]) == "SELECT 1"
    connection_context.__exit__.assert_called_once()


def test_database_readiness_rejects_unexpected_scalar() -> None:
    engine, _connection_context = _engine_returning(0)

    result = DatabaseReadinessCheck(engine)()

    assert result.status == "error"
    assert result.message == "資料庫檢查未回傳預期結果"


def test_database_readiness_hides_connection_exception() -> None:
    secret = "do-not-expose-this-password"
    engine = Mock(spec=Engine)
    engine.connect.side_effect = OperationalError(
        "connect",
        {},
        RuntimeError(secret),
    )

    result = DatabaseReadinessCheck(engine)()

    rendered = str(result.model_dump())
    assert result.status == "error"
    assert result.message == "無法連線至資料庫"
    assert secret not in rendered
