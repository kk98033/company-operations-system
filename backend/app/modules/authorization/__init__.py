"""Organization-scoped role-based authorization."""

from app.modules.authorization.capabilities import (
    has_capability,
    list_capabilities,
    validate_capability_code,
)
from app.modules.authorization.dependencies import require_capability

__all__ = [
    "has_capability",
    "list_capabilities",
    "require_capability",
    "validate_capability_code",
]
