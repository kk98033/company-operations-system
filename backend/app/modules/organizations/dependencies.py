"""FastAPI dependency for the organization bound to the current Session."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.modules.auth.dependencies import require_current_session
from app.modules.auth.services import AuthenticatedSession
from app.modules.organizations.scope import OrganizationScope


def require_organization_scope(
    context: Annotated[
        AuthenticatedSession,
        Depends(require_current_session),
    ],
) -> OrganizationScope:
    """Build scope only from server-resolved Session context."""

    return OrganizationScope(
        organization_id=context.organization_id,
        organization_member_id=context.organization_member_id,
        actor_user_id=context.user_id,
    )
