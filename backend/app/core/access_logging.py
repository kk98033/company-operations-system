"""Safe structured HTTP access logging without request secrets."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from uuid import UUID

from fastapi import Request, Response

access_logger = logging.getLogger("app.access")
application_logger = logging.getLogger("app.application")

SLOW_REQUEST_MILLISECONDS = 1_000
UNMATCHED_ROUTE = "<unmatched>"


def _configure_json_line_logger(logger: logging.Logger) -> None:
    if not any(
        getattr(handler, "_company_system_json_handler", False)
        for handler in logger.handlers
    ):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        handler._company_system_json_handler = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def configure_access_logger(*, emit_json_to_stderr: bool) -> None:
    """Use raw JSON lines outside tests so collectors can parse every field."""

    if not emit_json_to_stderr:
        return
    _configure_json_line_logger(access_logger)
    _configure_json_line_logger(application_logger)


@dataclass(frozen=True, slots=True)
class AccessActor:
    """Non-secret identity references safe for centralized access logs."""

    organization_id: UUID
    user_id: UUID
    organization_member_id: UUID
    session_id: UUID | None


def attach_access_actor(request: Request, *, actor: AccessActor) -> None:
    """Attach a validated server-side actor to the current request only."""

    request.state.access_actor = actor


def mark_request_error(request: Request, *, error_code: str) -> None:
    """Expose only the stable public error code to the access logger."""

    request.state.error_code = error_code


def request_started() -> float:
    """Capture a monotonic request start for duration measurement."""

    return perf_counter()


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    route_path = getattr(route, "path", None)
    return route_path if isinstance(route_path, str) else UNMATCHED_ROUTE


def _response_size(response: Response | None) -> int | None:
    if response is None:
        return None
    raw_size = response.headers.get("content-length")
    if raw_size is None:
        return None
    try:
        size = int(raw_size)
    except ValueError:
        return None
    return size if size >= 0 else None


def _safe_uuid(value: object) -> str | None:
    return str(value) if isinstance(value, UUID) else None


def build_access_record(
    request: Request,
    *,
    response: Response | None,
    status_code: int,
    started_at: float,
    finished_at: float | None = None,
) -> dict[str, Any]:
    """Build the allowlisted access record; never inspect path/query/body/headers."""

    actor = getattr(request.state, "access_actor", None)
    actor_values = asdict(actor) if isinstance(actor, AccessActor) else {}
    duration_ms = round(
        max(0.0, (finished_at if finished_at is not None else perf_counter()) - started_at)
        * 1_000,
        3,
    )
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "event": "http_access",
        "request_id": _safe_uuid(getattr(request.state, "request_id", None)),
        "method": request.method,
        "route": _route_template(request),
        "status_code": status_code,
        "duration_ms": duration_ms,
        "response_size_bytes": _response_size(response),
        "slow_request": duration_ms >= SLOW_REQUEST_MILLISECONDS,
        "error_code": getattr(request.state, "error_code", None),
        "organization_id": _safe_uuid(actor_values.get("organization_id")),
        "user_id": _safe_uuid(actor_values.get("user_id")),
        "organization_member_id": _safe_uuid(
            actor_values.get("organization_member_id")
        ),
        "session_id": _safe_uuid(actor_values.get("session_id")),
    }


def emit_access_log(
    request: Request,
    *,
    response: Response | None,
    status_code: int,
    started_at: float,
) -> None:
    """Emit exactly one machine-parseable JSON access event."""

    record = build_access_record(
        request,
        response=response,
        status_code=status_code,
        started_at=started_at,
    )
    level = logging.ERROR if status_code >= 500 else logging.INFO
    if status_code >= 400 or record["slow_request"]:
        level = max(level, logging.WARNING)
    access_logger.log(
        level,
        json.dumps(record, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
        extra={"access_record": record},
    )


def emit_application_error(
    *,
    request_id: UUID | None,
    exception_type: str,
) -> None:
    """Emit a safe structured application failure without exception content."""

    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "event": "application_error",
        "request_id": _safe_uuid(request_id),
        "exception_type": exception_type,
    }
    application_logger.error(
        json.dumps(record, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
        extra={"application_record": record, **record},
    )
