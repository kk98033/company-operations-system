"""Create reusable customer work-item specifications."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_customer_work_items"
down_revision: str | Sequence[str] | None = "0012_master_data"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint("uq_customers_organization_id_id", "customers", ["organization_id", "id"])
    op.create_table(
        "customer_work_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("specification", sa.Text(), nullable=True),
        sa.Column("unit_price", sa.Numeric(14, 4), nullable=True),
        sa.Column("source", sa.String(16), server_default="manual", nullable=False),
        sa.Column("source_reference", sa.String(128), nullable=True),
        sa.Column("legacy_source_table", sa.String(64), nullable=True),
        sa.Column("legacy_source_key", sa.String(128), nullable=True),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("btrim(code) <> ''", name="ck_customer_work_items_code_nonblank"),
        sa.CheckConstraint("btrim(name) <> ''", name="ck_customer_work_items_name_nonblank"),
        sa.CheckConstraint("status IN ('active', 'inactive')", name="ck_customer_work_items_status_allowed"),
        sa.CheckConstraint("source IN ('manual', 'legacy', 'work_order')", name="ck_customer_work_items_source_allowed"),
        sa.CheckConstraint("unit_price IS NULL OR unit_price >= 0", name="ck_customer_work_items_unit_price_nonnegative"),
        sa.CheckConstraint("(legacy_source_table IS NULL) = (legacy_source_key IS NULL)", name="ck_customer_work_items_legacy_source_pair"),
        sa.ForeignKeyConstraint(["organization_id", "customer_id"], ["customers.organization_id", "customers.id"], name="fk_customer_work_items_customer_scope", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_customer_work_items"),
    )
    op.create_index("uq_customer_work_items_customer_normalized_code", "customer_work_items", ["organization_id", "customer_id", sa.text("lower(btrim(code))")], unique=True)
    op.create_index("ix_customer_work_items_customer_status_name", "customer_work_items", ["organization_id", "customer_id", "status", "name", "id"])


def downgrade() -> None:
    op.drop_index("ix_customer_work_items_customer_status_name", table_name="customer_work_items")
    op.drop_index("uq_customer_work_items_customer_normalized_code", table_name="customer_work_items")
    op.drop_table("customer_work_items")
    op.drop_constraint("uq_customers_organization_id_id", "customers", type_="unique")
