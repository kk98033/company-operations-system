"""Top-level API v1 router."""

from collections.abc import Sequence

from fastapi import APIRouter

from app.api.v1.health import build_health_router
from app.core.readiness import ReadinessCheck


def build_v1_router(readiness_checks: Sequence[ReadinessCheck]) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    router.include_router(build_health_router(readiness_checks))
    return router
