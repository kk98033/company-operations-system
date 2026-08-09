"""Application exceptions and the public API error envelope."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

_PUBLIC_HTTP_HEADERS = frozenset(
    {
        "allow",
        "retry-after",
        "www-authenticate",
    }
)

_PUBLIC_VALIDATION_ERROR_TYPES = frozenset(
    {
        "bool_parsing",
        "bool_type",
        "date_from_datetime_parsing",
        "date_parsing",
        "date_type",
        "decimal_parsing",
        "enum",
        "float_parsing",
        "float_type",
        "greater_than",
        "greater_than_equal",
        "int_parsing",
        "int_type",
        "less_than",
        "less_than_equal",
        "list_type",
        "missing",
        "string_too_long",
        "string_too_short",
        "string_type",
        "time_parsing",
        "time_type",
        "uuid_parsing",
        "uuid_type",
        "value_error",
    }
)


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
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        self.headers = headers


def error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: Any | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    """Build one consistent response without leaking exception internals."""

    body = ErrorResponse(
        error=ErrorBody(code=code, message=message, details=details)
    )
    response_headers = {
        "Cache-Control": "no-store",
        "Pragma": "no-cache",
    }
    response_headers.update(headers or {})
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(body),
        headers=response_headers,
    )


def _http_error_code(status_code: int) -> str:
    known_codes = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        500: "INTERNAL_SERVER_ERROR",
        503: "SERVICE_NOT_READY",
    }
    return known_codes.get(status_code, "HTTP_ERROR")


def _http_error_message(status_code: int) -> str:
    known_messages = {
        400: "請求格式錯誤",
        401: "尚未通過身分驗證",
        403: "沒有執行此操作的權限",
        404: "找不到要求的資源",
        405: "不允許使用此 HTTP method",
        409: "資料狀態衝突",
        422: "請檢查輸入資料",
        500: "伺服器發生未預期錯誤",
        503: "服務尚未就緒",
    }
    return known_messages.get(status_code, "HTTP 請求失敗")


def _safe_http_headers(headers: Mapping[str, str] | None) -> dict[str, str]:
    """Preserve protocol headers without forwarding arbitrary metadata."""

    if headers is None:
        return {}
    return {
        name: value
        for name, value in headers.items()
        if name.lower() in _PUBLIC_HTTP_HEADERS
    }


def _safe_validation_message(error_type: str) -> str:
    if error_type == "missing":
        return "此欄位為必填"
    if error_type == "enum":
        return "值不在允許範圍"
    if error_type in {
        "greater_than",
        "greater_than_equal",
        "less_than",
        "less_than_equal",
    }:
        return "數值超出允許範圍"
    if error_type in {"string_too_long", "string_too_short"}:
        return "文字長度不符合限制"
    if error_type.endswith("_parsing") or error_type.endswith("_type"):
        return "格式不正確"
    return "輸入資料無效"


def _safe_validation_type(error_type: object) -> str:
    if isinstance(error_type, str) and error_type in _PUBLIC_VALIDATION_ERROR_TYPES:
        return error_type
    return "value_error"


def _safe_validation_details(exc: RequestValidationError) -> list[dict[str, Any]]:
    """Expose validation location and reason without echoing submitted values."""

    details: list[dict[str, Any]] = []
    for error in exc.errors():
        error_type = _safe_validation_type(error.get("type"))
        details.append(
            {
                "loc": list(error.get("loc", ())),
                "msg": _safe_validation_message(error_type),
                "type": error_type,
            }
        )
    return details


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
            headers=_safe_http_headers(exc.headers),
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
            details=_safe_validation_details(exc),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        _request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        return error_response(
            status_code=exc.status_code,
            code=_http_error_code(exc.status_code),
            message=_http_error_message(exc.status_code),
            headers=_safe_http_headers(exc.headers),
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(
        _request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.error(
            "Unhandled API error",
            extra={"exception_type": type(exc).__name__},
        )
        return error_response(
            status_code=500,
            code="INTERNAL_SERVER_ERROR",
            message="伺服器發生未預期錯誤",
        )
