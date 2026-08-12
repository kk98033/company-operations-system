"""Public contracts for the current company's printable profile."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OrganizationLogoMetadata(BaseModel):
    original_filename: str
    content_type: str
    sha256: str


class OrganizationProfileResponse(BaseModel):
    id: UUID
    name: str
    tax_identifier: str | None
    representative_name: str | None
    phone: str | None
    fax: str | None
    email: str | None
    address: str | None
    logo: OrganizationLogoMetadata | None
    updated_at: datetime


class OrganizationProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_updated_at: datetime
    name: str = Field(min_length=1, max_length=200)
    tax_identifier: str | None = Field(default=None, max_length=20)
    representative_name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=32)
    fax: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=254)
    address: str | None = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("name must be nonblank")
        return normalized

    @field_validator(
        "tax_identifier",
        "representative_name",
        "phone",
        "fax",
        "email",
        "address",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None
