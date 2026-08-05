"""Shared declarative metadata for future business models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Single metadata root imported by Alembic."""
