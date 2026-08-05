"""Unit tests for lazy engine construction and lifecycle ownership."""

from unittest.mock import Mock, patch

from sqlalchemy import Engine

from app.core.database.resources import create_database_resources
from tests.settings_factory import make_test_settings


def test_create_database_resources_is_lazy_and_uses_bounded_pool() -> None:
    engine = Mock(spec=Engine)
    session_factory = Mock()

    with (
        patch(
            "app.core.database.resources.create_engine",
            return_value=engine,
        ) as create_engine,
        patch(
            "app.core.database.resources.sessionmaker",
            return_value=session_factory,
        ) as build_session_factory,
    ):
        resources = create_database_resources(make_test_settings())

    assert resources.engine is engine
    assert resources.session_factory is session_factory
    engine.connect.assert_not_called()
    create_engine.assert_called_once_with(
        make_test_settings().database_url_value(),
        connect_args={"connect_timeout": 5},
        echo=False,
        hide_parameters=True,
        pool_pre_ping=True,
        pool_recycle=1_800,
        pool_size=5,
        max_overflow=2,
        pool_timeout=5,
    )
    build_session_factory.assert_called_once_with(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )


def test_database_resources_dispose_delegates_to_engine() -> None:
    engine = Mock(spec=Engine)
    resources = create_database_resources

    with patch(
        "app.core.database.resources.create_engine",
        return_value=engine,
    ):
        configured = resources(make_test_settings())

    configured.dispose()

    engine.dispose.assert_called_once_with()
