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
from app.modules.customers.models import Customer
from app.modules.imports.models import (
    ImportError,
    ImportRun,
    ImportSourceFile,
    ImportStagingRecord,
    LegacyMapping,
)
from app.modules.organizations.models import (
    Organization,
    OrganizationMember,
    OrganizationSettings,
)

REGISTERED_MODELS = (
    ImportError,
    ImportRun,
    ImportSourceFile,
    ImportStagingRecord,
    LegacyMapping,
    Organization,
    OrganizationSettings,
    Customer,
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
