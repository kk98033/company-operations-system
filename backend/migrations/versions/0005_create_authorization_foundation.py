"""Create organization-scoped role and capability foundations.

Revision ID: 0005_authorization_foundation
Revises: 0004_identity_foundation
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_authorization_foundation"
down_revision: str | Sequence[str] | None = "0004_identity_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create authorization tables without deciding the P1-02 role matrix."""

    op.create_unique_constraint(
        "uq_organization_members_organization_id_id",
        "organization_members",
        ["organization_id", "id"],
    )
    op.create_table(
        "permissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(128), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(16), server_default="active", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "code = lower(btrim(code)) AND "
            "code ~ '^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)+$'",
            name="ck_permissions_code_format",
        ),
        sa.CheckConstraint(
            "btrim(name) <> ''", name="ck_permissions_name_nonblank"
        ),
        sa.CheckConstraint(
            "status IN ('active', 'inactive')",
            name="ck_permissions_status_allowed",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_permissions_code"),
    )
    op.create_table(
        "roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(16), server_default="active", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "code = lower(btrim(code)) AND "
            "code ~ '^[a-z][a-z0-9_]*$'",
            name="ck_roles_code_format",
        ),
        sa.CheckConstraint("btrim(name) <> ''", name="ck_roles_name_nonblank"),
        sa.CheckConstraint(
            "status IN ('active', 'inactive')",
            name="ck_roles_status_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_roles_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "code", name="uq_roles_organization_id_code"
        ),
        sa.UniqueConstraint(
            "organization_id", "id", name="uq_roles_organization_id_id"
        ),
    )
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("permission_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permissions.id"],
            name="fk_role_permissions_permission_id_permissions",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            name="fk_role_permissions_role_id_roles",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )
    op.create_index(
        "ix_role_permissions_permission_id",
        "role_permissions",
        ["permission_id"],
    )
    op.create_table(
        "organization_member_roles",
        sa.Column("organization_member_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "organization_member_id"],
            ["organization_members.organization_id", "organization_members.id"],
            name=(
                "fk_organization_member_roles_member_"
                "organization_members"
            ),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "role_id"],
            ["roles.organization_id", "roles.id"],
            name="fk_organization_member_roles_role_roles",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("organization_member_id", "role_id"),
    )
    op.create_index(
        "ix_organization_member_roles_organization_id",
        "organization_member_roles",
        ["organization_id"],
    )
    op.create_index(
        "ix_organization_member_roles_role_id",
        "organization_member_roles",
        ["role_id"],
    )


def downgrade() -> None:
    """Remove authorization tables while preserving identity rows."""

    op.drop_table("organization_member_roles")
    op.drop_table("role_permissions")
    op.drop_table("roles")
    op.drop_table("permissions")
    op.drop_constraint(
        "uq_organization_members_organization_id_id",
        "organization_members",
        type_="unique",
    )
