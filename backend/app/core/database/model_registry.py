"""Explicit model registry loaded by Alembic before metadata comparison."""

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
from app.modules.imports.models import (
    ImportError,
    ImportRun,
    ImportSourceFile,
    ImportStagingRecord,
    LegacyMapping,
)
from app.modules.master_data.models import PaperMill, PaperType, ProcessDefinition, Vendor
from app.modules.organizations.models import (
    Organization,
    OrganizationMember,
    OrganizationSettings,
)
from app.modules.production.models import (
    FinalCompletionEntry,
    InventoryAdjustment,
    InventoryLedgerEntry,
    ProcessEvent,
)
from app.modules.quotations.models import DocumentSequence, Quotation, QuotationItem
from app.modules.shipments.models import Shipment, ShipmentItem
from app.modules.work_orders.models import ProductionCase, WorkOrder, WorkOrderAttachment

REGISTERED_MODELS = (
    ImportError,
    ImportRun,
    ImportSourceFile,
    ImportStagingRecord,
    LegacyMapping,
    Organization,
    OrganizationSettings,
    Customer,
    CustomerWorkItem,
    DocumentSequence,
    Quotation,
    QuotationItem,
    ProductionCase,
    WorkOrder,
    WorkOrderAttachment,
    ProcessEvent,
    FinalCompletionEntry,
    InventoryAdjustment,
    InventoryLedgerEntry,
    Shipment,
    ShipmentItem,
    Vendor,
    PaperType,
    PaperMill,
    ProcessDefinition,
    User,
    OrganizationMember,
    Session,
    LoginThrottleState,
    LoginSecurityEvent,
    Permission,
    Role,
    RolePermission,
    OrganizationMemberRole,
    AuditLog,
)

__all__ = ["REGISTERED_MODELS"]
