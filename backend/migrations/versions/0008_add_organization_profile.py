"""Add printable company profile and logo metadata.

Revision ID: 0008_organization_profile
Revises: 0007_login_security
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_organization_profile"
down_revision: str | Sequence[str] | None = "0007_login_security"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Extend the existing organization boundary without importing legacy data."""

    columns = (
        sa.Column("tax_identifier", sa.String(20), nullable=True),
        sa.Column("representative_name", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("fax", sa.String(32), nullable=True),
        sa.Column("email", sa.String(254), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("logo_object_key", sa.String(512), nullable=True),
        sa.Column("logo_content_type", sa.String(100), nullable=True),
        sa.Column("logo_original_filename", sa.String(255), nullable=True),
        sa.Column("logo_sha256", sa.String(64), nullable=True),
    )
    for column in columns:
        op.add_column("organizations", column)

    optional_nonblank = (
        "tax_identifier",
        "representative_name",
        "phone",
        "fax",
        "email",
        "address",
    )
    for name in optional_nonblank:
        op.create_check_constraint(
            f"ck_organizations_{name}_nonblank",
            "organizations",
            f"{name} IS NULL OR btrim({name}) <> ''",
        )
    op.create_check_constraint(
        "ck_organizations_logo_sha256_format",
        "organizations",
        "logo_sha256 IS NULL OR logo_sha256 ~ '^[0-9a-f]{64}$'",
    )
    op.create_check_constraint(
        "ck_organizations_logo_metadata_complete",
        "organizations",
        "(logo_object_key IS NULL AND logo_content_type IS NULL "
        "AND logo_original_filename IS NULL AND logo_sha256 IS NULL) OR "
        "(logo_object_key IS NOT NULL AND logo_content_type IS NOT NULL "
        "AND logo_original_filename IS NOT NULL AND logo_sha256 IS NOT NULL)",
    )


def downgrade() -> None:
    """Remove profile metadata while preserving the organization identity root."""

    for name in (
        "ck_organizations_logo_metadata_complete",
        "ck_organizations_logo_sha256_format",
        "ck_organizations_address_nonblank",
        "ck_organizations_email_nonblank",
        "ck_organizations_fax_nonblank",
        "ck_organizations_phone_nonblank",
        "ck_organizations_representative_name_nonblank",
        "ck_organizations_tax_identifier_nonblank",
    ):
        op.drop_constraint(name, "organizations", type_="check")
    for name in (
        "logo_sha256",
        "logo_original_filename",
        "logo_content_type",
        "logo_object_key",
        "address",
        "email",
        "fax",
        "phone",
        "representative_name",
        "tax_identifier",
    ):
        op.drop_column("organizations", name)
