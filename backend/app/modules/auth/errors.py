"""Domain errors for authentication without HTTP coupling."""


class AuthenticationFailedError(RuntimeError):
    """Credentials or active organization membership were not accepted."""


class SessionCreationError(RuntimeError):
    """A login session could not be persisted atomically."""
