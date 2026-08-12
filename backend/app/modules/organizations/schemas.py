"""Public contracts for the current company's printable profile."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class StatementTaxDefaults(BaseModel):
    enabled: bool
    tax_rate_percent: Decimal | None
    rounding_scope: Literal["per_line", "grand_total"] | None
    rounding_decimal_places: int | None
    calculation_status: Literal["pending_phase_8_uat"]


class DocumentNumberPolicyResponse(BaseModel):
    document_type: str
    label: str
    format: str
    reset_period: Literal["daily", "monthly"]


class PrintPolicyResponse(BaseModel):
    document_type: str
    label: str
    paper_size: Literal["A4"]
    orientation: Literal["landscape", "portrait"] | None
    status: Literal["confirmed", "pending_uat"]
    note: str


class OrganizationSettingsResponse(BaseModel):
    organization_id: UUID
    statement_tax: StatementTaxDefaults
    document_number_policy_version: Literal["adr-018-v1"]
    document_numbering: list[DocumentNumberPolicyResponse]
    quotation_print_layout_version: Literal["gmail-a4-landscape-v1"]
    work_order_print_layout_version: Literal["gmail-a4-portrait-9-process-v1"]
    printing: list[PrintPolicyResponse]
    updated_at: datetime


class OrganizationSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_updated_at: datetime
    statement_tax_default_enabled: bool
    statement_tax_rate_percent: Decimal | None = Field(default=None, gt=0, le=100, decimal_places=4)
    statement_rounding_scope: Literal["per_line", "grand_total"] | None = None
    statement_rounding_decimal_places: int | None = Field(default=None, ge=0, le=4)

    @model_validator(mode="after")
    def require_complete_tax_policy(self) -> "OrganizationSettingsUpdate":
        conditional = (
            self.statement_tax_rate_percent,
            self.statement_rounding_scope,
            self.statement_rounding_decimal_places,
        )
        if self.statement_tax_default_enabled and any(value is None for value in conditional):
            raise ValueError("enabled statement tax requires rate and rounding fields")
        if not self.statement_tax_default_enabled and any(
            value is not None for value in conditional
        ):
            raise ValueError("disabled statement tax must not carry active tax fields")
        return self
