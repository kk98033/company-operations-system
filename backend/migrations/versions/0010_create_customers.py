"""Create organization-scoped customer master records."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_customers"
down_revision: str | Sequence[str] | None = "0009_organization_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("short_name", sa.String(100), nullable=True),
        sa.Column("tax_identifier", sa.String(20), nullable=True),
        sa.Column("contact_name", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("phone_secondary", sa.String(32), nullable=True),
        sa.Column("mobile", sa.String(32), nullable=True),
        sa.Column("fax", sa.String(32), nullable=True),
        sa.Column("email", sa.String(254), nullable=True),
        sa.Column("postal_code", sa.String(16), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("btrim(code) <> ''", name="ck_customers_code_nonblank"),
        sa.CheckConstraint("btrim(name) <> ''", name="ck_customers_name_nonblank"),
        sa.CheckConstraint("status IN ('active', 'inactive')", name="ck_customers_status_allowed"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_customers_organization_id_organizations", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_customers"),
    )
    op.create_index(
        "uq_customers_organization_normalized_code", "customers",
        ["organization_id", sa.text("lower(btrim(code))")], unique=True,
    )
    op.create_index(
        "ix_customers_organization_status_name", "customers",
        ["organization_id", "status", "name", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_customers_organization_status_name", table_name="customers")
    op.drop_index("uq_customers_organization_normalized_code", table_name="customers")
    op.drop_table("customers")
