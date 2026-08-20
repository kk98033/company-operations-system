"""Add a safe client summary for Session management.

Revision ID: 0026_session_management
Revises: 0025_session_replacement
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026_session_management"
down_revision: str | Sequence[str] | None = "0025_session_replacement"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Store only a broad browser/platform label, never the raw User-Agent."""

    op.add_column(
        "sessions",
        sa.Column("client_summary", sa.String(length=80), nullable=True),
    )


def downgrade() -> None:
    """Remove the optional display-only summary."""

    op.drop_column("sessions", "client_summary")
