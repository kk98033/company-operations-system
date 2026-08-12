"""Unit contracts for opaque login security primitives."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.modules.auth.login_security import (
    advisory_lock_key,
    derive_login_fingerprint,
    retry_after_seconds,
)


def test_login_fingerprint_is_deterministic_opaque_and_company_scoped() -> None:
    organization_id = uuid4()
    key = b"k" * 32
    normalized_login = "sensitive.operator"

    fingerprint = derive_login_fingerprint(
        organization_id=organization_id,
        normalized_login_bucket=normalized_login,
        signing_key=key,
    )
    same_bucket = derive_login_fingerprint(
        organization_id=organization_id,
        normalized_login_bucket=normalized_login,
        signing_key=key,
    )
    other_company = derive_login_fingerprint(
        organization_id=uuid4(),
        normalized_login_bucket=normalized_login,
        signing_key=key,
    )
    tab_distinct = derive_login_fingerprint(
        organization_id=organization_id,
        normalized_login_bucket=f"\t{normalized_login}\t",
        signing_key=key,
    )

    assert fingerprint == same_bucket
    assert fingerprint != other_company
    assert fingerprint != tab_distinct
    assert len(fingerprint) == 64
    assert "sensitive" not in fingerprint
    assert -(2**63) <= advisory_lock_key(fingerprint) < 2**63


def test_retry_after_rounds_up_and_never_returns_zero() -> None:
    timestamp = datetime.now(UTC)

    assert retry_after_seconds(
        blocked_until=timestamp + timedelta(microseconds=1),
        timestamp=timestamp,
    ) == 1
