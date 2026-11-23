from __future__ import annotations


class HuntbaseError(Exception):
    """Base error for the Huntbase integration."""


class HuntbaseConfigurationError(HuntbaseError):
    """The integration or action configuration is invalid."""


class HuntbaseApiError(HuntbaseError):
    """Huntbase answered with an error status."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class HuntbaseAuthError(HuntbaseApiError):
    """The API key was rejected (401)."""


class HuntbasePermissionError(HuntbaseApiError):
    """The API key is valid but may not call this route (403)."""


class HuntbaseNotFoundError(HuntbaseApiError):
    """The requested item does not exist (404)."""


class HuntbaseRateLimitError(HuntbaseApiError):
    """Huntbase kept answering 429 after retries."""


class HuntbaseConnectionError(HuntbaseError):
    """Huntbase could not be reached."""
