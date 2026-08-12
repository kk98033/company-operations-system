"""Company-scoped settings queries and audited updates."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.modules.audit import record_user_audit_event
from app.modules.organizations.models import OrganizationSettings
from app.modules.organizations.schemas import OrganizationSettingsUpdate
from app.modules.organizations.scope import OrganizationScope

EDITABLE_SETTINGS_FIELDS = (
    "statement_tax_default_enabled",
    "statement_tax_rate_percent",
    "statement_rounding_scope",
    "statement_rounding_decimal_places",
)


class OrganizationSettingsConflictError(RuntimeError):
    """The client attempted to overwrite settings changed by another editor."""


def new_organization_settings(organization_id: UUID) -> OrganizationSettings:
    """Build safe defaults for the company-creation transaction."""

    return OrganizationSettings(organization_id=organization_id)


def get_organization_settings(
    session: OrmSession,
    *,
    scope: OrganizationScope,
) -> OrganizationSettings:
    """Load settings only for the organization carried by the Session."""

    return session.execute(
        select(OrganizationSettings).where(
            OrganizationSettings.organization_id == scope.organization_id
        )
    ).scalar_one()


def update_organization_settings(
    session: OrmSession,
    *,
    scope: OrganizationScope,
    payload: OrganizationSettingsUpdate,
    request_id: UUID,
) -> OrganizationSettings:
    """Replace editable defaults and audit them in one transaction."""

    try:
        settings = session.execute(
            select(OrganizationSettings)
            .where(OrganizationSettings.organization_id == scope.organization_id)
            .with_for_update()
        ).scalar_one()
        if settings.updated_at != payload.expected_updated_at:
            raise OrganizationSettingsConflictError

        before = {field: getattr(settings, field) for field in EDITABLE_SETTINGS_FIELDS}
        values = payload.model_dump(exclude={"expected_updated_at"})
        for field, value in values.items():
            setattr(settings, field, value)
        settings.updated_at = datetime.now(UTC)
        session.flush()
        after = {field: getattr(settings, field) for field in EDITABLE_SETTINGS_FIELDS}
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="organization.settings_update",
            entity_type="organization_settings",
            entity_id=settings.organization_id,
            before=before,
            after=after,
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return settings
