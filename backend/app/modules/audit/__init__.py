"""Append-only audit domain."""

from app.modules.audit.services import record_user_audit_event

__all__ = ["record_user_audit_event"]
