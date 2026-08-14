"""Shared authorization context for cross-module read models."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.modules.auth.services import AuthenticatedSession
from app.modules.authorization.capabilities import list_capabilities
from app.modules.organizations.scope import OrganizationScope


@dataclass(frozen=True, slots=True)
class OperationsContext:
    scope: OrganizationScope
    capabilities: frozenset[str]

    def can(self, capability: str) -> bool:
        return capability in self.capabilities


def build_operations_context(session: Session, identity: AuthenticatedSession) -> OperationsContext:
    return OperationsContext(
        scope=OrganizationScope(
            organization_id=identity.organization_id,
            organization_member_id=identity.organization_member_id,
            actor_user_id=identity.user_id,
        ),
        capabilities=frozenset(
            list_capabilities(
                session,
                organization_member_id=identity.organization_member_id,
                organization_id=identity.organization_id,
            )
        ),
    )
