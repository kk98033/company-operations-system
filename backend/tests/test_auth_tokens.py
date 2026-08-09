"""Unit tests for opaque authentication token primitives."""

from hashlib import sha256
from secrets import token_urlsafe

import pytest
from pydantic import SecretStr

from app.modules.auth.tokens import (
    SESSION_TOKEN_BYTES,
    SESSION_TOKEN_LENGTH,
    digest_session_token,
    is_session_token_format,
    issue_session_token,
)


def test_issued_token_has_256_bits_and_only_exposes_a_digest_for_storage() -> None:
    issued = issue_session_token()
    raw_value = issued.raw.get_secret_value()

    assert len(raw_value) == SESSION_TOKEN_LENGTH
    assert is_session_token_format(raw_value)
    assert len(issued.digest) == 64
    assert issued.digest == sha256(raw_value.encode()).hexdigest()
    assert raw_value not in issued.digest
    assert raw_value not in repr(issued.raw)


def test_digest_is_deterministic_for_a_runtime_only_secret() -> None:
    raw_token = SecretStr(token_urlsafe(SESSION_TOKEN_BYTES))

    assert digest_session_token(raw_token) == digest_session_token(raw_token)


@pytest.mark.parametrize(
    "invalid_value",
    ["", "short", "A" * 42, "A" * 44, "A" * 42 + "="],
)
def test_token_format_rejects_values_the_service_does_not_issue(
    invalid_value: str,
) -> None:
    assert is_session_token_format(invalid_value) is False


def test_issuer_rejects_an_incompatible_generator_without_echoing_value() -> None:
    invalid_value = token_urlsafe(16)

    with pytest.raises(RuntimeError) as error:
        issue_session_token(lambda _size: invalid_value)

    assert invalid_value not in str(error.value)
