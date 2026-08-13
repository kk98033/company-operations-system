"""Create production cases.

Revision ID: 0016_production_cases
Revises: 0015_quotations
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_production_cases"
down_revision: str | Sequence[str] | None = "0015_quotations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "production_cases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("case_number", sa.String(32), nullable=False),
        sa.Column("case_date", sa.Date(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("organization_snapshot", sa.JSON(), nullable=False),
        sa.Column("customer_snapshot", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), server_default="draft", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source_quotation_id", sa.Uuid(), nullable=True),
        sa.Column("legacy_document_number", sa.String(128), nullable=True),
        sa.Column("legacy_source_table", sa.String(64), nullable=True),
        sa.Column("legacy_source_key", sa.String(128), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("void_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'void')", name="ck_production_cases_status"
        ),
        sa.CheckConstraint("btrim(case_number) <> ''", name="ck_production_cases_number_nonblank"),
        sa.CheckConstraint(
            "(status = 'void' AND voided_at IS NOT NULL AND btrim(void_reason) <> '') OR (status <> 'void' AND voided_at IS NULL AND void_reason IS NULL)",
            name="ck_production_cases_void_state",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_production_cases_org",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
            name="fk_production_cases_customer_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "source_quotation_id"],
            ["quotations.organization_id", "quotations.id"],
            name="fk_production_cases_quotation_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "id", name="uq_production_cases_org_id"),
    )
    op.create_index(
        "uq_production_cases_org_number",
        "production_cases",
        ["organization_id", "case_number"],
        unique=True,
    )
    op.create_index(
        "uq_production_cases_org_source_quote",
        "production_cases",
        ["organization_id", "source_quotation_id"],
        unique=True,
        postgresql_where=sa.text("source_quotation_id IS NOT NULL"),
    )
    op.create_index(
        "ix_production_cases_org_date_status",
        "production_cases",
        ["organization_id", "case_date", "status", "id"],
    )


def downgrade() -> None:
    op.drop_table("production_cases")
