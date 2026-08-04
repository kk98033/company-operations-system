"""Injectable dependency readiness checks."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Literal

from pydantic import BaseModel


class ReadinessCheckResult(BaseModel):
    """One necessary dependency's current readiness state."""

    name: str
    status: Literal["ok", "error", "not_configured"]
    message: str | None = None


ReadinessCheck = Callable[[], ReadinessCheckResult]


def database_not_configured() -> ReadinessCheckResult:
    """Temporary explicit result until SQLAlchemy is introduced in Slice 0.5."""

    return ReadinessCheckResult(
        name="database",
        status="not_configured",
        message="資料庫就緒檢查將在 Slice 0.5 建立",
    )


def run_readiness_checks(
    checks: Sequence[ReadinessCheck],
) -> list[ReadinessCheckResult]:
    """Run the small synchronous checks configured for this process."""

    results: list[ReadinessCheckResult] = []
    for check in checks:
        try:
            results.append(check())
        except Exception:
            results.append(
                ReadinessCheckResult(
                    name=getattr(check, "__name__", "unknown"),
                    status="error",
                    message="檢查執行失敗",
                )
            )
    return results
