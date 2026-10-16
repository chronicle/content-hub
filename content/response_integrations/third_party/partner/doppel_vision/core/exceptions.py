from __future__ import annotations


class DoppelError(Exception):
    """Base error for the DoppelVision integration."""


class DoppelConfigError(DoppelError):
    """Raised when instance configuration is missing or invalid."""


class DoppelHttpError(DoppelError):
    """Raised when a Doppel API request fails."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(message)
