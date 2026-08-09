"""OpenAPI metadata and shared error response documentation."""

from __future__ import annotations

from typing import Any

from app.core.errors import ErrorResponse

API_TITLE = "公司管理系統 API"
API_DESCRIPTION = "公司內部報價、工單、生產、出貨與帳務系統 API。"
API_VERSION = "0.1.0"
API_TAGS = [
    {
        "name": "auth",
        "description": "登入、登出與伺服器 Session 狀態。",
    },
    {
        "name": "health",
        "description": "進程存活與必要相依服務就緒狀態。",
    }
]


def build_default_error_responses() -> dict[int | str, dict[str, Any]]:
    """Return fresh OpenAPI response definitions for common API failures."""

    descriptions = {
        400: "請求格式錯誤",
        401: "尚未通過身分驗證",
        403: "沒有執行此操作的權限",
        404: "資源不存在",
        405: "HTTP method 不允許用於此資源",
        409: "資料狀態或版本衝突",
        422: "輸入資料驗證失敗",
        500: "伺服器發生未預期錯誤",
    }
    return {
        status_code: {
            "model": ErrorResponse,
            "description": description,
        }
        for status_code, description in descriptions.items()
    }
