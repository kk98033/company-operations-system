"""Domain errors for authentication without HTTP coupling."""


class AuthenticationFailedError(RuntimeError):
    """Credentials or active organization membership were not accepted."""


class LoginRateLimitedError(RuntimeError):
    """The opaque login bucket is temporarily blocked."""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("login attempt temporarily limited")
        self.retry_after_seconds = retry_after_seconds


class SessionCreationError(RuntimeError):
    """A login session could not be persisted atomically."""
