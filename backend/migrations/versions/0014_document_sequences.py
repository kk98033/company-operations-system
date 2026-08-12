"""Create company document number sequences."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_document_sequences"
down_revision: str | Sequence[str] | None = "0013_customer_work_items"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_sequences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("document_type", sa.String(32), nullable=False),
        sa.Column("period_key", sa.String(16), nullable=False),
        sa.Column("next_value", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("next_value >= 1", name="ck_document_sequences_next_value_positive"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_document_sequences_organization",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document_sequences"),
    )
    op.create_index(
        "uq_document_sequences_scope",
        "document_sequences",
        ["organization_id", "document_type", "period_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_document_sequences_scope", table_name="document_sequences")
    op.drop_table("document_sequences")
