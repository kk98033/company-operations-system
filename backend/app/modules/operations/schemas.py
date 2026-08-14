"""Typed contracts for cross-module operational read models."""

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class DashboardCard(BaseModel):
    key: str
    label: str
    value: Decimal
    unit: str
    target_path: str
    tone: Literal["neutral", "warning", "danger", "success"] = "neutral"


class DashboardResponse(BaseModel):
    as_of: date
    cards: list[DashboardCard]


class SearchResult(BaseModel):
    entity_type: Literal[
        "customer", "quotation", "case", "work_order", "shipment", "pricing", "statement", "receipt"
    ]
    entity_id: UUID
    primary_text: str
    secondary_text: str | None = None
    status: str | None = None
    target_path: str


class SearchResponse(BaseModel):
    keyword: str
    items: list[SearchResult]
    truncated: bool


class CustomerActivity(BaseModel):
    entity_type: Literal[
        "quotation", "case", "work_order", "shipment", "pricing", "statement", "receipt"
    ]
    entity_id: UUID
    document_number: str
    activity_date: date
    summary: str
    status: str
    target_path: str


class CustomerOverviewResponse(BaseModel):
    customer_id: UUID
    customer_code: str
    customer_name: str
    customer_status: str
    counts: dict[str, int]
    outstanding_amount: Decimal | None = None
    recent_activity: list[CustomerActivity] = Field(max_length=30)
