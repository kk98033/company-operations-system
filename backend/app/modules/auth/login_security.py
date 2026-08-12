"""Privacy-preserving login fingerprint and throttle policy primitives."""

from __future__ import annotations

import hashlib
import hmac
import math
from datetime import datetime, timedelta
from uuid import UUID

LOGIN_FAILURE_LIMIT = 5
LOGIN_FAILURE_WINDOW = timedelta(minutes=15)
LOGIN_BLOCK_DURATION = timedelta(minutes=15)


def derive_login_fingerprint(
    *,
    organization_id: UUID,
    normalized_login_bucket: str,
    signing_key: bytes,
) -> str:
    """Return an opaque key from a database-normalized login bucket."""

    payload = (
        f"login-throttle-v1\0{organization_id}\0{normalized_login_bucket}"
    ).encode()
    return hmac.new(signing_key, payload, hashlib.sha256).hexdigest()


def advisory_lock_key(fingerprint: str) -> int:
    """Map a fingerprint to a signed PostgreSQL advisory-lock key."""

    unsigned = int(fingerprint[:16], 16)
    return unsigned if unsigned < 2**63 else unsigned - 2**64


def retry_after_seconds(*, blocked_until: datetime, timestamp: datetime) -> int:
    """Return a positive whole-second Retry-After value."""

    return max(1, math.ceil((blocked_until - timestamp).total_seconds()))
