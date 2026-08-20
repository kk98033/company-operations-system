"""Public API contracts for login and server-side sessions."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr, field_validator


class LoginRequest(BaseModel):
    login_name: str = Field(min_length=1, max_length=128)
    password: SecretStr = Field(min_length=1, max_length=256)
    organization_id: UUID


class AuthenticatedUserResponse(BaseModel):
    id: UUID
    login_name: str
    display_name: str


class AuthenticatedOrganizationResponse(BaseModel):
    id: UUID
    name: str


class CurrentSessionResponse(BaseModel):
    expires_at: datetime
    user: AuthenticatedUserResponse
    organization: AuthenticatedOrganizationResponse
    capabilities: list[str]


class LoginResponse(CurrentSessionResponse):
    pass


class ManagedSessionResponse(BaseModel):
    id: UUID
    organization_member_id: UUID
    user: AuthenticatedUserResponse
    client_summary: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    status: Literal["active", "expired", "revoked", "identity_inactive"]
    is_current: bool


class ManagedSessionListResponse(BaseModel):
    items: list[ManagedSessionResponse]
    total_items: int


class SessionRevocationRequest(BaseModel):
    reason: str = Field(min_length=2, max_length=500)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("reason must contain at least two nonblank characters")
        return normalized


class MembershipSessionRevocationRequest(SessionRevocationRequest):
    organization_member_id: UUID
