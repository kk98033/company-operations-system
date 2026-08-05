"""Establish an empty migration baseline.

Revision ID: 0001_empty_baseline
Revises: None
Create Date: 2026-08-06
"""

from collections.abc import Sequence

revision: str = "0001_empty_baseline"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Keep the baseline empty until a signed-off business migration."""


def downgrade() -> None:
    """Revert the empty baseline without touching application data."""
