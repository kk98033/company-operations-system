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
from app.core.config import AppEnvironment, AppSettings, load_settings
from app.core.errors import register_exception_handlers
from app.core.readiness import ReadinessCheck, database_not_configured


def create_app(
    *,
    settings: AppSettings | None = None,
    readiness_checks: Sequence[ReadinessCheck] | None = None,
) -> FastAPI:
    """Create an isolated app with validated settings and injected checks."""

    configured_settings = settings or load_settings()
    expose_api_docs = configured_settings.environment is not AppEnvironment.PRODUCTION

    app = FastAPI(
        title=API_TITLE,
        description=API_DESCRIPTION,
        version=API_VERSION,
        docs_url="/docs" if expose_api_docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if expose_api_docs else None,
        openapi_tags=API_TAGS,
        responses=build_default_error_responses(),
    )
    app.state.settings = configured_settings
    register_exception_handlers(app)

    configured_checks = (
        tuple(readiness_checks)
        if readiness_checks is not None
        else (database_not_configured,)
    )
    app.include_router(build_v1_router(configured_checks))
    return app


app = create_app()
