"""Unit contracts for Session-bound CSRF signatures."""

from secrets import token_urlsafe

from pydantic import SecretStr

from app.modules.auth.csrf import (
    CSRF_TOKEN_LENGTH,
    csrf_token_matches,
    derive_csrf_token,
)
from tests.settings_factory import make_test_settings


def test_csrf_token_is_urlsafe_and_bound_to_one_session_and_key() -> None:
    settings = make_test_settings()
    first_session = SecretStr(token_urlsafe(32))
    second_session = SecretStr(token_urlsafe(32))
    token = derive_csrf_token(
        first_session,
        signing_key=settings.csrf_hmac_key_value(),
    ).get_secret_value()

    assert len(token) == CSRF_TOKEN_LENGTH
    assert token.replace("-", "").replace("_", "").isalnum()
    assert token != derive_csrf_token(
        second_session,
        signing_key=settings.csrf_hmac_key_value(),
    ).get_secret_value()
    assert csrf_token_matches(
        first_session,
        signing_key=settings.csrf_hmac_key_value(),
        cookie_token=token,
        header_token=token,
    )
    assert not csrf_token_matches(
        second_session,
        signing_key=settings.csrf_hmac_key_value(),
        cookie_token=token,
        header_token=token,
    )
    assert not csrf_token_matches(
        first_session,
        signing_key=b"different-signing-key-material!",
        cookie_token=token,
        header_token=token,
    )


def test_matching_attacker_controlled_values_are_not_accepted() -> None:
    forged = "A" * CSRF_TOKEN_LENGTH
    raw_session = SecretStr(token_urlsafe(32))

    assert not csrf_token_matches(
        raw_session,
        signing_key=make_test_settings().csrf_hmac_key_value(),
        cookie_token=forged,
        header_token=forged,
    )
