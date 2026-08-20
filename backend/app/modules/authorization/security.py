"""Authorization-denial evidence shared by dependency and manual guards."""

from uuid import UUID

from sqlalchemy.orm import Session as OrmSession

from app.modules.auth.services import (
    AuthenticatedSession,
    record_authenticated_security_event,
)


def persist_permission_denial(
    session: OrmSession,
    *,
    context: AuthenticatedSession,
    request_id: UUID,
    capability: str,
) -> None:
    """Commit one denial event; fail closed when evidence cannot be stored."""

    try:
        record_authenticated_security_event(
            session,
            context=context,
            request_id=request_id,
            event_type="permission_denied",
            capability=capability,
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
