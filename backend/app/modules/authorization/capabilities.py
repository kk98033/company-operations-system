"""Capability code validation and organization-scoped resolution."""

from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.modules.auth.models import User
from app.modules.authorization.models import (
    OrganizationMemberRole,
    Permission,
    Role,
    RolePermission,
)
from app.modules.organizations.models import Organization, OrganizationMember

_CAPABILITY_CODE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")


def validate_capability_code(code: str) -> str:
    """Reject developer configuration that cannot match the DB contract."""

    if not _CAPABILITY_CODE.fullmatch(code):
        raise ValueError("capability code must use normalized action segments")
    return code


def list_capabilities(
    session: OrmSession,
    *,
    organization_member_id: UUID,
    organization_id: UUID,
) -> tuple[str, ...]:
    """Return active grants for one membership, never from another company."""

    rows = session.scalars(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(
            OrganizationMemberRole,
            OrganizationMemberRole.role_id == Role.id,
        )
        .join(
            OrganizationMember,
            OrganizationMember.id
            == OrganizationMemberRole.organization_member_id,
        )
        .join(User, User.id == OrganizationMember.user_id)
        .join(Organization, Organization.id == OrganizationMember.organization_id)
        .where(
            OrganizationMemberRole.organization_member_id
            == organization_member_id,
            OrganizationMemberRole.organization_id == organization_id,
            Role.organization_id == organization_id,
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.status == "active",
            User.status == "active",
            Organization.status == "active",
            Role.status == "active",
            Permission.status == "active",
        )
        .distinct()
        .order_by(Permission.code)
    ).all()
    return tuple(rows)


def has_capability(
    session: OrmSession,
    *,
    organization_member_id: UUID,
    organization_id: UUID,
    capability: str,
) -> bool:
    """Check one exact capability without wildcard or role-name shortcuts."""

    validate_capability_code(capability)
    return capability in list_capabilities(
        session,
        organization_member_id=organization_member_id,
        organization_id=organization_id,
    )
