"""Public contracts for organization-scoped audit history."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.api.contracts import ListResponse, SortDirection, SortParams


class AuditSortField(StrEnum):
    CREATED_AT = "created_at"
    ACTION = "action"


class AuditSortParams(SortParams[AuditSortField]):
    sort_by: AuditSortField = AuditSortField.CREATED_AT
    sort_direction: SortDirection = SortDirection.DESC


class AuditFilterParams(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    keyword: str | None = Field(default=None, max_length=100)
    action: str | None = Field(default=None, max_length=128)
    entity_type: str | None = Field(default=None, max_length=64)
    request_id: UUID | None = None


class AuditLogResponse(BaseModel):
    id: UUID
    actor_user_id: UUID | None
    action: str
    entity_type: str
    entity_id: UUID | None
    document_number: str | None
    event_status: str
    reason: str | None
    before_data: dict[str, object] | None
    after_data: dict[str, object] | None
    request_id: UUID
    created_at: datetime


class AuditFilterSummary(AuditFilterParams):
    pass


AuditLogListResponse = ListResponse[AuditLogResponse, AuditFilterSummary]
