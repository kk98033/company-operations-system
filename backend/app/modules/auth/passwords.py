"""Argon2id password primitives without HTTP or session behavior."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from argon2.profiles import RFC_9106_LOW_MEMORY
from pydantic import SecretStr

_PASSWORD_HASHER = PasswordHasher.from_parameters(RFC_9106_LOW_MEMORY)


def hash_password(password: SecretStr) -> str:
    """Return an Argon2id hash while keeping the raw value wrapped as a secret."""

    return _PASSWORD_HASHER.hash(password.get_secret_value())


def verify_password(password: SecretStr, encoded_hash: str) -> bool:
    """Verify one secret for seed consistency without leaking failure details."""

    try:
        return _PASSWORD_HASHER.verify(encoded_hash, password.get_secret_value())
    except (InvalidHashError, VerificationError):
        return False
