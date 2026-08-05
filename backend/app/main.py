"""FastAPI application factory and default ASGI application."""

from __future__ import annotations

from collections.abc import Sequence

from fastapi import FastAPI

from app.api.v1.router import build_v1_router
from app.core.config import AppSettings, load_settings
from app.core.errors import register_exception_handlers
from app.core.readiness import ReadinessCheck, database_not_configured


def create_app(
    *,
    settings: AppSettings | None = None,
    readiness_checks: Sequence[ReadinessCheck] | None = None,
) -> FastAPI:
    """Create an isolated app with validated settings and injected checks."""

    configured_settings = settings or load_settings()

    app = FastAPI(
        title="公司管理系統 API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
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
