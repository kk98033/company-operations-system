"""Shared fixtures for isolated PostgreSQL integration tests."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, text

from app.core.database import create_database_resources
from app.modules.audit.models import AuditLog
from app.modules.auth.models import (
    LoginSecurityEvent,
    LoginThrottleState,
    Session,
    User,
)
from app.modules.authorization.models import (
    OrganizationMemberRole,
    Permission,
    Role,
    RolePermission,
)
from app.modules.customers.models import Customer, CustomerWorkItem
from app.modules.master_data.models import PaperMill, PaperType, ProcessDefinition, Vendor
from app.modules.organizations.models import (
    Organization,
    OrganizationMember,
    OrganizationSettings,
)
from app.modules.quotations.models import DocumentSequence, Quotation, QuotationItem
from app.modules.work_orders.models import ProductionCase, WorkOrder, WorkOrderAttachment
from tests.integration.database_settings import load_database_test_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def migrated_engine(monkeypatch: pytest.MonkeyPatch) -> Generator[Engine, None, None]:
    """Provide an engine after upgrading the isolated test database to head."""

    settings = load_database_test_settings()
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_HOST", settings.host)
    monkeypatch.setenv("APP_PORT", str(settings.port))
    monkeypatch.setenv("DATABASE_URL", settings.database_url_value())
    command.upgrade(Config(str(BACKEND_ROOT / "alembic.ini")), "head")

    resources = create_database_resources(settings)
    try:
        yield resources.engine
    finally:
        resources.dispose()


@pytest.fixture
def identity_engine(migrated_engine: Engine) -> Generator[Engine, None, None]:
    """Keep committed identity fixtures isolated from every neighboring test."""

    try:
        yield migrated_engine
    finally:
        with migrated_engine.begin() as connection:
            connection.execute(text(f"TRUNCATE TABLE {AuditLog.__tablename__}"))
            connection.execute(text(f"TRUNCATE TABLE {LoginSecurityEvent.__tablename__}"))
            connection.execute(LoginThrottleState.__table__.delete())
            connection.execute(Session.__table__.delete())
            connection.execute(OrganizationMemberRole.__table__.delete())
            connection.execute(RolePermission.__table__.delete())
            connection.execute(Role.__table__.delete())
            connection.execute(Permission.__table__.delete())
            connection.execute(
                text(
                    "TRUNCATE TABLE price_history, pricing_items, pricing_documents, "
                    "inventory_ledger, shipment_items, shipments, inventory_adjustments, "
                    "final_completion_entries, process_events"
                )
            )
            connection.execute(WorkOrderAttachment.__table__.delete())
            connection.execute(WorkOrder.__table__.delete())
            connection.execute(ProductionCase.__table__.delete())
            connection.execute(QuotationItem.__table__.delete())
            connection.execute(Quotation.__table__.delete())
            connection.execute(DocumentSequence.__table__.delete())
            connection.execute(CustomerWorkItem.__table__.delete())
            connection.execute(Customer.__table__.delete())
            connection.execute(Vendor.__table__.delete())
            connection.execute(PaperType.__table__.delete())
            connection.execute(PaperMill.__table__.delete())
            connection.execute(ProcessDefinition.__table__.delete())
            connection.execute(OrganizationSettings.__table__.delete())
            connection.execute(OrganizationMember.__table__.delete())
            connection.execute(User.__table__.delete())
            connection.execute(Organization.__table__.delete())
