"""Signed-off document and print policies exposed as read-only settings."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DocumentNumberPolicy:
    document_type: str
    label: str
    format: str
    reset_period: str


DOCUMENT_NUMBER_POLICIES = (
    DocumentNumberPolicy("quotation", "報價", "QUO-YYYYMMDD-SS", "daily"),
    DocumentNumberPolicy("case", "案件", "CASE-YYYYMMDD-SSS", "daily"),
    DocumentNumberPolicy("work_order", "工單", "WO-YYYYMMDD-SSS", "daily"),
    DocumentNumberPolicy("shipment", "出貨", "SHP-YYYYMM-SSS", "monthly"),
    DocumentNumberPolicy("pricing", "計價", "PRC-YYYYMMDD-SSS", "daily"),
    DocumentNumberPolicy("statement", "對帳", "STM-YYYYMM-SSS", "monthly"),
    DocumentNumberPolicy("receipt", "收款", "RCT-YYYYMMDD-SSS", "daily"),
)


@dataclass(frozen=True, slots=True)
class PrintPolicy:
    document_type: str
    label: str
    paper_size: str
    orientation: str | None
    status: str
    note: str


PRINT_POLICIES = (
    PrintPolicy(
        "quotation",
        "報價單",
        "A4",
        "landscape",
        "confirmed",
        "依公司報價單 A4 橫向稿固定，正式模板於 Phase 3 驗收。",
    ),
    PrintPolicy(
        "work_order",
        "工單",
        "A4",
        "portrait",
        "confirmed",
        "依公司工單 A4 直向稿固定；列印稿為 9 道製程。",
    ),
    PrintPolicy(
        "statement",
        "對帳單",
        "A4",
        None,
        "pending_uat",
        "公司尚未提供對帳單樣張，方向與版面留待 Phase 8 實印確認。",
    ),
)
