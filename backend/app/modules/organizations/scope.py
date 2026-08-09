"""Authenticated organization scope primitives for every business query."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID


class OrganizationScopeContractError(RuntimeError):
    """Application code attempted to bypass the authenticated organization."""


class CrossOrganizationReferenceError(RuntimeError):
    """A referenced row belongs to a different organization."""


@dataclass(frozen=True, slots=True)
class OrganizationScope:
    """Trusted company and actor IDs copied only from an active Session."""

    organization_id: UUID
    organization_member_id: UUID
    actor_user_id: UUID

    def constrain(self, statement: Any, *, model: type[Any]) -> Any:
        """Append the model's mandatory company predicate to a DB statement."""

        organization_column = getattr(model, "organization_id", None)
        if organization_column is None:
            raise OrganizationScopeContractError(
                "scoped model must declare organization_id"
            )
        return statement.where(organization_column == self.organization_id)

    def create_values(self, values: dict[str, object]) -> dict[str, object]:
        """Inject company ownership; callers may not supply it themselves."""

        if "organization_id" in values:
            raise OrganizationScopeContractError(
                "organization_id must come from authenticated scope"
            )
        return {**values, "organization_id": self.organization_id}

    def require_same_organization(self, organization_id: UUID) -> None:
        """Reject cross-company relation targets without exposing either ID."""

        if organization_id != self.organization_id:
            raise CrossOrganizationReferenceError(
                "referenced resource is unavailable in this organization"
            )
