"""FastAPI lifespan ownership for database resources."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from fastapi import FastAPI

from app.core.database.resources import DatabaseResources

AppLifespan = Callable[[FastAPI], AbstractAsyncContextManager[None]]


def build_database_lifespan(resources: DatabaseResources) -> AppLifespan:
    """Build an application lifespan that always disposes the engine."""

    @asynccontextmanager
    async def database_lifespan(_app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            resources.dispose()

    return database_lifespan
