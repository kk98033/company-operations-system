"""Password hashing contract used by non-production identity seeds."""

from secrets import token_urlsafe

from pydantic import SecretStr

from app.modules.auth.passwords import hash_password, verify_password


def test_argon2id_hash_never_contains_or_returns_the_raw_password() -> None:
    raw_password = token_urlsafe(24)
    password = SecretStr(raw_password)

    encoded_hash = hash_password(password)

    assert encoded_hash.startswith("$argon2id$")
    assert raw_password not in encoded_hash
    assert raw_password not in repr(password)
    assert verify_password(password, encoded_hash) is True
    assert verify_password(SecretStr(token_urlsafe(24)), encoded_hash) is False


def test_invalid_encoded_hash_is_rejected_without_raising() -> None:
    assert verify_password(SecretStr(token_urlsafe(24)), "not-a-hash") is False
