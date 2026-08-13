"""OpenAPI metadata and shared error response documentation."""

from __future__ import annotations

from typing import Any

from app.core.errors import ErrorResponse

API_TITLE = "公司管理系統 API"
API_DESCRIPTION = "公司內部報價、工單、生產、出貨與帳務系統 API。"
API_VERSION = "0.1.0"
API_TAGS = [
    {
        "name": "document-exports",
        "description": "建立、保存並下載具雜湊的公司文件 PDF。",
    },
    {
        "name": "billing",
        "description": "目前公司的對帳、請款狀態、收款分配與帳齡。",
    },
    {
        "name": "cases",
        "description": "目前公司的生產案件分組與報價轉工單。",
    },
    {
        "name": "audit",
        "description": "具權限者查詢目前公司的不可變操作紀錄。",
    },
    {
        "name": "auth",
        "description": "登入、登出與伺服器 Session 狀態。",
    },
    {
        "name": "customers",
        "description": "目前公司的客戶主檔查詢與維護。",
    },
    {
        "name": "health",
        "description": "進程存活與必要相依服務就緒狀態。",
    },
    {
        "name": "master-data",
        "description": "目前公司的供應商、紙材與固定製程主檔。",
    },
    {
        "name": "organizations",
        "description": "目前公司的基本資料、帳務預設與固定文件政策。",
    },
    {
        "name": "pricing",
        "description": "目前公司的出貨計價、額外明細與價格記憶。",
    },
    {
        "name": "production",
        "description": "目前公司的製程、最終完工與庫存流水。",
    },
    {
        "name": "quotations",
        "description": "目前公司的報價建檔、確認與查詢。",
    },
    {
        "name": "shipments",
        "description": "目前公司的部分、多次、備品與取消出貨。",
    },
    {
        "name": "work-orders",
        "description": "目前公司的單品工單建檔、確認、查詢與私人附件。",
    },
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
        429: "請求次數暫時超過安全限制",
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
