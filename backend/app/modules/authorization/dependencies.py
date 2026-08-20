"""FastAPI capability guard built on the authenticated Session context."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session as OrmSession

from app.core.database.session import get_database_session
from app.core.errors import ApplicationError
from app.core.request_context import require_request_id
from app.modules.auth.dependencies import require_current_session
from app.modules.auth.services import AuthenticatedSession
from app.modules.authorization.capabilities import (
    has_capability,
    validate_capability_code,
)
from app.modules.authorization.security import persist_permission_denial


def require_capability(
    capability: str,
) -> Callable[..., AuthenticatedSession]:
    """Build an exact deny-by-default API dependency for one capability."""

    checked_capability = validate_capability_code(capability)

    def dependency(
        request: Request,
        context: Annotated[
            AuthenticatedSession,
            Depends(require_current_session),
        ],
        database_session: Annotated[
            OrmSession,
            Depends(get_database_session),
        ],
    ) -> AuthenticatedSession:
        if not has_capability(
            database_session,
            organization_member_id=context.organization_member_id,
            organization_id=context.organization_id,
            capability=checked_capability,
        ):
            persist_permission_denial(
                database_session,
                context=context,
                request_id=require_request_id(request),
                capability=checked_capability,
            )
            raise ApplicationError(
                status_code=403,
                code="PERMISSION_DENIED",
                message="沒有執行此操作的權限",
            )
        return context

    return dependency
