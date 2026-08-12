"""Create company-scoped defaults and immutable policy versions.

Revision ID: 0009_organization_settings
Revises: 0008_organization_profile
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_organization_settings"
down_revision: str | Sequence[str] | None = "0008_organization_profile"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create one settings row per company and backfill safe defaults."""

    op.create_table(
        "organization_settings",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column(
            "statement_tax_default_enabled",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column("statement_tax_rate_percent", sa.Numeric(7, 4), nullable=True),
        sa.Column("statement_rounding_scope", sa.String(16), nullable=True),
        sa.Column("statement_rounding_decimal_places", sa.SmallInteger(), nullable=True),
        sa.Column(
            "document_number_policy_version",
            sa.String(32),
            server_default="adr-018-v1",
            nullable=False,
        ),
        sa.Column(
            "quotation_print_layout_version",
            sa.String(64),
            server_default="gmail-a4-landscape-v1",
            nullable=False,
        ),
        sa.Column(
            "work_order_print_layout_version",
            sa.String(64),
            server_default="gmail-a4-portrait-9-process-v1",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "statement_rounding_scope IS NULL OR "
            "statement_rounding_scope IN ('per_line', 'grand_total')",
            name="ck_organization_settings_rounding_scope_allowed",
        ),
        sa.CheckConstraint(
            "statement_rounding_decimal_places IS NULL OR "
            "statement_rounding_decimal_places BETWEEN 0 AND 4",
            name="ck_organization_settings_rounding_places_range",
        ),
        sa.CheckConstraint(
            "(statement_tax_default_enabled = false "
            "AND statement_tax_rate_percent IS NULL "
            "AND statement_rounding_scope IS NULL "
            "AND statement_rounding_decimal_places IS NULL) OR "
            "(statement_tax_default_enabled = true "
            "AND statement_tax_rate_percent > 0 "
            "AND statement_tax_rate_percent <= 100 "
            "AND statement_rounding_scope IS NOT NULL "
            "AND statement_rounding_decimal_places IS NOT NULL)",
            name="ck_organization_settings_statement_tax_complete",
        ),
        sa.CheckConstraint(
            "document_number_policy_version = 'adr-018-v1'",
            name="ck_organization_settings_number_policy_v1",
        ),
        sa.CheckConstraint(
            "quotation_print_layout_version = 'gmail-a4-landscape-v1'",
            name="ck_organization_settings_quotation_print_v1",
        ),
        sa.CheckConstraint(
            "work_order_print_layout_version = 'gmail-a4-portrait-9-process-v1'",
            name="ck_organization_settings_work_order_print_v1",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_organization_settings_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("organization_id", name="pk_organization_settings"),
    )
    op.execute(
        sa.text("INSERT INTO organization_settings (organization_id) SELECT id FROM organizations")
    )


def downgrade() -> None:
    """Remove defaults without touching company identity or profile data."""

    op.drop_table("organization_settings")
