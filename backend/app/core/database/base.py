"""Shared declarative metadata for infrastructure and future business models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Single metadata root imported by Alembic."""
