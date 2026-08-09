"""Public API contracts for login and server-side sessions."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr

from app.modules.auth.tokens import SESSION_TOKEN_LENGTH


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


class LoginResponse(CurrentSessionResponse):
    session_token: str = Field(
        min_length=SESSION_TOKEN_LENGTH,
        max_length=SESSION_TOKEN_LENGTH,
        repr=False,
    )
    token_type: Literal["Bearer"]
