"""Real PostgreSQL readiness check built on SQLAlchemy."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.readiness import ReadinessCheckResult


@dataclass(frozen=True, slots=True)
class DatabaseReadinessCheck:
    """Execute a bounded, read-only query against the configured database."""

    engine: Engine
    __name__ = "database"

    def __call__(self) -> ReadinessCheckResult:
        try:
            with self.engine.connect() as connection:
                is_available = connection.scalar(text("SELECT 1")) == 1
        except SQLAlchemyError:
            return ReadinessCheckResult(
                name="database",
                status="error",
                message="無法連線至資料庫",
            )

        if not is_available:
            return ReadinessCheckResult(
                name="database",
                status="error",
                message="資料庫檢查未回傳預期結果",
            )
        return ReadinessCheckResult(name="database", status="ok")
