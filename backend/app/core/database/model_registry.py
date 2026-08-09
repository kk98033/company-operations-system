"""Explicit model registry loaded by Alembic before metadata comparison."""

from app.modules.auth.models import Session, User
from app.modules.imports.models import (
    ImportError,
    ImportRun,
    ImportSourceFile,
    ImportStagingRecord,
    LegacyMapping,
)
from app.modules.organizations.models import Organization, OrganizationMember

REGISTERED_MODELS = (
    ImportError,
    ImportRun,
    ImportSourceFile,
    ImportStagingRecord,
    LegacyMapping,
    Organization,
    User,
    OrganizationMember,
    Session,
)

__all__ = ["REGISTERED_MODELS"]
