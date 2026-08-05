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
