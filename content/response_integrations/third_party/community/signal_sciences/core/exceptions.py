from __future__ import annotations


class SignalSciencesIntegrationError(Exception):
    """Base exception for SignalSciences integration."""


class SignalSciencesIntegrationHTTPError(SignalSciencesIntegrationError):
    """HTTP error for SignalSciences integration."""
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
