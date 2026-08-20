"""Organization-scoped role-based authorization."""

from app.modules.authorization.capabilities import (
    has_capability,
    list_capabilities,
    validate_capability_code,
)
from app.modules.authorization.dependencies import require_capability
from app.modules.authorization.security import persist_permission_denial

__all__ = [
    "has_capability",
    "list_capabilities",
    "require_capability",
    "persist_permission_denial",
    "validate_capability_code",
]
