"""Create vendors, paper catalogs, and confirmed process definitions."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_master_data"
down_revision: str | Sequence[str] | None = "0011_customer_legacy_billing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PROCESS_VALUES = (
    ("artwork", "美工", 1),
    ("output", "輸出", 2),
    ("plate_making", "製版", 3),
    ("proofing", "打樣", 4),
    ("printing", "印刷", 5),
    ("coating", "上光", 6),
    ("laminating", "裱紙", 7),
    ("die_making", "模具", 8),
    ("die_cutting", "軋型", 9),
    ("finishing", "加工", 10),
    ("gluing", "糊邊", 11),
    ("delivery", "運送", 12),
    ("other", "其他", 13),
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "vendors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("short_name", sa.String(100), nullable=True),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("contact_name", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("phone_secondary", sa.String(32), nullable=True),
        sa.Column("mobile", sa.String(32), nullable=True),
        sa.Column("fax", sa.String(32), nullable=True),
        sa.Column("email", sa.String(254), nullable=True),
        sa.Column("postal_code", sa.String(16), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("settlement_day", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        *_timestamps(),
        sa.CheckConstraint("btrim(code) <> ''", name="ck_vendors_code_nonblank"),
        sa.CheckConstraint("btrim(name) <> ''", name="ck_vendors_name_nonblank"),
        sa.CheckConstraint(
            "category IN ('supplier', 'collaborator')", name="ck_vendors_category_allowed"
        ),
        sa.CheckConstraint("status IN ('active', 'inactive')", name="ck_vendors_status_allowed"),
        sa.CheckConstraint(
            "settlement_day IS NULL OR settlement_day BETWEEN 1 AND 31",
            name="ck_vendors_settlement_day_range",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_vendors_organization",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_vendors"),
    )
    op.create_index(
        "uq_vendors_organization_normalized_code",
        "vendors",
        ["organization_id", sa.text("lower(btrim(code))")],
        unique=True,
    )
    op.create_index(
        "ix_vendors_organization_status_name",
        "vendors",
        ["organization_id", "status", "name", "id"],
    )
    _create_catalog("paper_types")
    _create_catalog("paper_mills")
    op.create_table(
        "process_definitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_system", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        *_timestamps(),
        sa.CheckConstraint("btrim(code) <> ''", name="ck_process_definitions_code_nonblank"),
        sa.CheckConstraint("btrim(name) <> ''", name="ck_process_definitions_name_nonblank"),
        sa.CheckConstraint(
            "status IN ('active', 'inactive')", name="ck_process_definitions_status_allowed"
        ),
        sa.CheckConstraint("sort_order BETWEEN 1 AND 13", name="ck_process_definitions_sort_range"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_process_definitions_organization",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_process_definitions"),
    )
    op.create_index(
        "uq_process_definitions_org_code",
        "process_definitions",
        ["organization_id", "code"],
        unique=True,
    )
    op.create_index(
        "uq_process_definitions_org_sort",
        "process_definitions",
        ["organization_id", "sort_order"],
        unique=True,
    )
    _create_process_trigger()


def _create_catalog(table: str) -> None:
    prefix = table
    op.create_table(
        table,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        *_timestamps(),
        sa.CheckConstraint("btrim(code) <> ''", name=f"ck_{prefix}_code_nonblank"),
        sa.CheckConstraint("btrim(name) <> ''", name=f"ck_{prefix}_name_nonblank"),
        sa.CheckConstraint("status IN ('active', 'inactive')", name=f"ck_{prefix}_status_allowed"),
        sa.CheckConstraint("sort_order >= 0", name=f"ck_{prefix}_sort_nonnegative"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=f"fk_{prefix}_organization",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=f"pk_{prefix}"),
    )
    op.create_index(
        f"uq_{prefix}_org_code",
        table,
        ["organization_id", sa.text("lower(btrim(code))")],
        unique=True,
    )
    op.create_index(
        f"uq_{prefix}_org_name",
        table,
        ["organization_id", sa.text("lower(btrim(name))")],
        unique=True,
    )
    op.create_index(
        f"ix_{prefix}_org_sort", table, ["organization_id", "status", "sort_order", "id"]
    )


def _create_process_trigger() -> None:
    values = ", ".join(f"('{code}', '{name}', {order})" for code, name, order in PROCESS_VALUES)
    op.execute(
        sa.text(f"""
        INSERT INTO process_definitions (id, organization_id, code, name, sort_order)
        SELECT gen_random_uuid(), organizations.id, seed.code, seed.name, seed.sort_order
        FROM organizations CROSS JOIN (VALUES {values}) AS seed(code, name, sort_order)
    """)
    )
    op.execute(
        sa.text(f"""
        CREATE FUNCTION seed_process_definitions_for_organization() RETURNS trigger AS $$
        BEGIN
          INSERT INTO process_definitions (id, organization_id, code, name, sort_order)
          SELECT gen_random_uuid(), NEW.id, seed.code, seed.name, seed.sort_order
          FROM (VALUES {values}) AS seed(code, name, sort_order);
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER trg_organizations_seed_process_definitions
        AFTER INSERT ON organizations FOR EACH ROW
        EXECUTE FUNCTION seed_process_definitions_for_organization();
    """)
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_organizations_seed_process_definitions ON organizations")
    op.execute("DROP FUNCTION IF EXISTS seed_process_definitions_for_organization()")
    op.drop_table("process_definitions")
    op.drop_table("paper_mills")
    op.drop_table("paper_types")
    op.drop_table("vendors")
