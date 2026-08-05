"""Process liveness and dependency readiness endpoints."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.errors import ApplicationError, ErrorResponse
from app.core.readiness import ReadinessCheck, ReadinessCheckResult, run_readiness_checks


class LiveResponse(BaseModel):
    status: Literal["alive"]
    service: Literal["company-system-api"]


class ReadyResponse(BaseModel):
    status: Literal["ready"]
    checks: list[ReadinessCheckResult]


def build_health_router(checks: Sequence[ReadinessCheck]) -> APIRouter:
    router = APIRouter(prefix="/health", tags=["health"])

    @router.get(
        "/live",
        response_model=LiveResponse,
        operation_id="health_live",
        summary="檢查 API 進程是否存活",
    )
    def live() -> LiveResponse:
        """Report process liveness without calling external dependencies."""

        return LiveResponse(status="alive", service="company-system-api")

    @router.get(
        "/ready",
        response_model=ReadyResponse,
        operation_id="health_ready",
        summary="檢查必要相依服務是否就緒",
        responses={
            503: {
                "model": ErrorResponse,
                "description": "必要相依服務尚未就緒",
            }
        },
    )
    def ready() -> ReadyResponse:
        """Report whether every configured required dependency is available."""

        results = run_readiness_checks(checks)
        if any(result.status != "ok" for result in results):
            raise ApplicationError(
                status_code=503,
                code="SERVICE_NOT_READY",
                message="必要相依服務尚未就緒",
                details={"checks": [result.model_dump() for result in results]},
            )
        return ReadyResponse(status="ready", checks=results)

    return router
