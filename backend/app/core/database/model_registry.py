"""Explicit model registry loaded by Alembic before metadata comparison."""

from app.modules.imports.models import (
    ImportError,
    ImportRun,
    ImportSourceFile,
    ImportStagingRecord,
    LegacyMapping,
)

REGISTERED_MODELS = (
    ImportError,
    ImportRun,
    ImportSourceFile,
    ImportStagingRecord,
    LegacyMapping,
)

__all__ = ["REGISTERED_MODELS"]
