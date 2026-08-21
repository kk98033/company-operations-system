"""FastAPI application factory and default ASGI application."""

from __future__ import annotations

from collections.abc import Sequence

from fastapi import FastAPI

from app.api.contracts.openapi import (
    API_DESCRIPTION,
    API_TAGS,
    API_TITLE,
    API_VERSION,
    build_default_error_responses,
)
from app.api.v1.router import build_v1_router
from app.core.access_logging import configure_access_logger
from app.core.config import AppEnvironment, AppSettings, load_settings
from app.core.database import (
    DatabaseReadinessCheck,
    DatabaseResources,
    create_database_resources,
)
from app.core.database.lifecycle import build_database_lifespan
from app.core.errors import register_exception_handlers
from app.core.readiness import ReadinessCheck
from app.core.request_context import attach_request_id


def create_app(
    *,
    settings: AppSettings | None = None,
    database_resources: DatabaseResources | None = None,
    readiness_checks: Sequence[ReadinessCheck] | None = None,
) -> FastAPI:
    """Create an app that owns and disposes its database resources."""

    configured_settings = settings or load_settings()
    configured_database = database_resources or create_database_resources(
        configured_settings
    )
    expose_api_docs = configured_settings.environment is not AppEnvironment.PRODUCTION
    configure_access_logger(
        emit_json_to_stderr=configured_settings.environment is not AppEnvironment.TEST
    )

    app = FastAPI(
        title=API_TITLE,
        description=API_DESCRIPTION,
        version=API_VERSION,
        docs_url="/docs" if expose_api_docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if expose_api_docs else None,
        openapi_tags=API_TAGS,
        responses=build_default_error_responses(),
        lifespan=build_database_lifespan(configured_database),
    )
    app.state.settings = configured_settings
    app.state.database = configured_database
    app.middleware("http")(attach_request_id)
    register_exception_handlers(app)

    configured_checks = (
        tuple(readiness_checks)
        if readiness_checks is not None
        else (DatabaseReadinessCheck(configured_database.engine),)
    )
    app.include_router(build_v1_router(configured_checks))
    return app


app = create_app()
