"""Server-generated request correlation context."""

from __future__ import annotations

from contextvars import ContextVar, Token
from uuid import UUID, uuid4

from fastapi import Request, Response
from starlette.middleware.base import RequestResponseEndpoint

REQUEST_ID_HEADER = "X-Request-ID"
_request_id: ContextVar[UUID | None] = ContextVar("request_id", default=None)


def current_request_id() -> UUID | None:
    """Return the current request ID for structured logging."""

    return _request_id.get()


def require_request_id(request: Request) -> UUID:
    """Load the ID created by middleware, never from client input."""

    request_id = getattr(request.state, "request_id", None)
    if not isinstance(request_id, UUID):
        raise RuntimeError("request ID middleware is not installed")
    return request_id


async def attach_request_id(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    """Create a fresh UUID for every request and expose it in the response."""

    request_id = uuid4()
    request.state.request_id = request_id
    token: Token[UUID | None] = _request_id.set(request_id)
    try:
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = str(request_id)
        return response
    finally:
        _request_id.reset(token)
