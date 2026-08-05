"""Application ownership tests for injected database resources."""

from unittest.mock import Mock

from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.main import create_app
from tests.database_factory import make_database_resources
from tests.settings_factory import make_test_settings


def test_app_disposes_injected_database_resources_at_shutdown() -> None:
    engine = Mock(spec=Engine)
    resources = make_database_resources(engine=engine)
    app = create_app(
        settings=make_test_settings(),
        database_resources=resources,
        readiness_checks=[],
    )

    with TestClient(app) as client:
        assert client.get("/api/v1/health/live").status_code == 200
        engine.dispose.assert_not_called()

    engine.dispose.assert_called_once_with()
    assert app.state.database is resources
