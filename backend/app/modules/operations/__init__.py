"""Cross-module operations dashboard, search, customer view, and exports."""

from app.modules.operations.api import build_operations_router

__all__ = ["build_operations_router"]
