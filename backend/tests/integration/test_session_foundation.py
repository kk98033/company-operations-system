"""PostgreSQL acceptance tests for digest-only server sessions."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError

from app.modules.auth.models import Session, User
from app.modules.organizations.models import Organization, OrganizationMember
from tests.integration.identity_test_support import (
    assert_insert_rejected,
    seed_identity,
)

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1",
        reason="requires explicit isolated PostgreSQL integration run",
    ),
]


def test_session_membership_foreign_key_is_enforced(
    identity_engine: Engine,
) -> None:
    now = datetime.now(UTC)
    assert_insert_rejected(
        identity_engine,
        Session.__table__,
        {
            "id": uuid4(),
            "organization_member_id": uuid4(),
            "token_digest": "e" * 64,
            "created_at": now,
            "expires_at": now + timedelta(hours=8),
        },
    )


def test_sessions_store_only_digest_and_validate_lifecycle(
    identity_engine: Engine,
) -> None:
    _, _, member_id, _ = seed_identity(identity_engine)
    now = datetime.now(UTC)
    raw_token = f"synthetic-raw-token-never-persisted-{member_id}"
    token_digest = sha256(raw_token.encode()).hexdigest()
    session_values = {
        "id": uuid4(),
        "organization_member_id": member_id,
        "token_digest": token_digest,
        "created_at": now,
        "expires_at": now + timedelta(hours=8),
        "last_seen_at": now,
    }
    with identity_engine.begin() as connection:
        connection.execute(Session.__table__.insert(), session_values)
        stored_digest = connection.scalar(
            Session.__table__.select()
            .with_only_columns(Session.token_digest)
            .where(Session.id == session_values["id"])
        )
    assert stored_digest == token_digest
    assert stored_digest != raw_token

    for invalid_values in (
        {**session_values, "id": uuid4(), "token_digest": "raw-session-token"},
        {**session_values, "id": uuid4(), "token_digest": token_digest},
        {
            **session_values,
            "id": uuid4(),
            "token_digest": "b" * 64,
            "expires_at": now - timedelta(seconds=1),
        },
        {
            **session_values,
            "id": uuid4(),
            "token_digest": "c" * 64,
            "revoked_at": now - timedelta(seconds=1),
        },
        {
            **session_values,
            "id": uuid4(),
            "token_digest": "f" * 64,
            "last_seen_at": now - timedelta(seconds=1),
        },
    ):
        assert_insert_rejected(identity_engine, Session.__table__, invalid_values)


def test_identity_parents_cannot_be_deleted_while_referenced(
    identity_engine: Engine,
) -> None:
    organization_id, user_id, member_id, _ = seed_identity(identity_engine)
    now = datetime.now(UTC)
    with identity_engine.begin() as connection:
        connection.execute(
            Session.__table__.insert(),
            {
                "id": uuid4(),
                "organization_member_id": member_id,
                "token_digest": sha256(str(member_id).encode()).hexdigest(),
                "created_at": now,
                "expires_at": now + timedelta(hours=8),
                "last_seen_at": now,
            },
        )

    for table, identifier in (
        (Organization.__table__, organization_id),
        (User.__table__, user_id),
        (OrganizationMember.__table__, member_id),
    ):
        with identity_engine.connect() as connection:
            with pytest.raises(IntegrityError):
                with connection.begin():
                    connection.execute(table.delete().where(table.c.id == identifier))
