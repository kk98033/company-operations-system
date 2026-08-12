"""Scoped company-profile queries and audited updates."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.modules.audit import record_user_audit_event
from app.modules.organizations.models import Organization
from app.modules.organizations.schemas import OrganizationProfileUpdate
from app.modules.organizations.scope import OrganizationScope

EDITABLE_PROFILE_FIELDS = (
    "name",
    "tax_identifier",
    "representative_name",
    "phone",
    "fax",
    "email",
    "address",
)


class OrganizationProfileConflictError(RuntimeError):
    """The client attempted to overwrite a profile changed by another editor."""


def get_organization_profile(
    session: OrmSession,
    *,
    scope: OrganizationScope,
) -> Organization:
    """Load exactly the organization bound to the authenticated Session."""

    return session.execute(
        select(Organization).where(Organization.id == scope.organization_id)
    ).scalar_one()


def update_organization_profile(
    session: OrmSession,
    *,
    scope: OrganizationScope,
    payload: OrganizationProfileUpdate,
    request_id: UUID,
) -> Organization:
    """Replace editable profile fields and audit them in one transaction."""

    try:
        organization = session.execute(
            select(Organization)
            .where(Organization.id == scope.organization_id)
            .with_for_update()
        ).scalar_one()
        if organization.updated_at != payload.expected_updated_at:
            raise OrganizationProfileConflictError

        before = {
            field: getattr(organization, field) for field in EDITABLE_PROFILE_FIELDS
        }
        values = payload.model_dump(exclude={"expected_updated_at"})
        for field, value in values.items():
            setattr(organization, field, value)
        organization.updated_at = datetime.now(UTC)
        session.flush()
        after = {
            field: getattr(organization, field) for field in EDITABLE_PROFILE_FIELDS
        }
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="organization.profile_update",
            entity_type="organization",
            entity_id=organization.id,
            before=before,
            after=after,
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return organization
