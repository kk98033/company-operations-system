"""Add active payment terms and read-only legacy billing evidence."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_customer_legacy_billing"
down_revision: str | Sequence[str] | None = "0010_customers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("payment_terms", sa.String(200), nullable=True))
    op.add_column("customers", sa.Column("legacy_tax_setting_raw", sa.String(16), nullable=True))
    op.add_column(
        "customers", sa.Column("legacy_rounding_setting_raw", sa.String(16), nullable=True)
    )
    op.add_column("customers", sa.Column("legacy_source_table", sa.String(64), nullable=True))
    op.add_column("customers", sa.Column("legacy_source_key", sa.String(128), nullable=True))
    op.create_check_constraint(
        "ck_customers_legacy_source_pair",
        "customers",
        "(legacy_source_table IS NULL) = (legacy_source_key IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_customers_legacy_source_pair", "customers", type_="check")
    for column in (
        "legacy_source_key",
        "legacy_source_table",
        "legacy_rounding_setting_raw",
        "legacy_tax_setting_raw",
        "payment_terms",
    ):
        op.drop_column("customers", column)
