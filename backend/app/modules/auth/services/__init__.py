"""Authentication application services."""

from app.modules.auth.services.login import LoginResult, create_login_session
from app.modules.auth.services.security_events import record_authenticated_security_event
from app.modules.auth.services.session import (
    AuthenticatedSession,
    get_active_session,
    revoke_session,
)
from app.modules.auth.services.session_management import (
    ManagedSession,
    list_company_sessions,
    list_personal_sessions,
    revoke_managed_session,
    revoke_membership_sessions,
)

__all__ = [
    "AuthenticatedSession",
    "LoginResult",
    "ManagedSession",
    "create_login_session",
    "get_active_session",
    "list_company_sessions",
    "list_personal_sessions",
    "revoke_managed_session",
    "revoke_membership_sessions",
    "revoke_session",
    "record_authenticated_security_event",
]
