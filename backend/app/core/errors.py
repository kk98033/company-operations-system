"""Application exceptions and the public API error envelope."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ErrorBody(BaseModel):
    """Stable, machine-readable API error fields."""

    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    """Public JSON envelope for every handled API error."""

    error: ErrorBody


class ApplicationError(Exception):
    """Expected application failure safe to expose to API clients."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: Any | None = None,
) -> JSONResponse:
    """Build one consistent response without leaking exception internals."""

    body = ErrorResponse(
        error=ErrorBody(code=code, message=message, details=details)
    )
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(body),
    )


def _http_error_code(status_code: int) -> str:
    known_codes = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
    }
    return known_codes.get(status_code, "HTTP_ERROR")


def register_exception_handlers(app: FastAPI) -> None:
    """Install the API-wide error contract on a FastAPI application."""

    @app.exception_handler(ApplicationError)
    async def application_error_handler(
        _request: Request,
        exc: ApplicationError,
    ) -> JSONResponse:
        return error_response(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return error_response(
            status_code=422,
            code="VALIDATION_ERROR",
            message="請檢查輸入資料",
            details=exc.errors(),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        _request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "HTTP 請求失敗"
        details = None if isinstance(exc.detail, str) else exc.detail
        return error_response(
            status_code=exc.status_code,
            code=_http_error_code(exc.status_code),
            message=message,
            details=details,
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(
        _request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception("Unhandled API error", exc_info=exc)
        return error_response(
            status_code=500,
            code="INTERNAL_SERVER_ERROR",
            message="伺服器發生未預期錯誤",
        )
