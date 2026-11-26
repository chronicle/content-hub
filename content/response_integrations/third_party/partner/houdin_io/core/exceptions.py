from __future__ import annotations


class HoudinError(Exception):
    """An answer from Houdin that is not the one asked for, carrying the API's own message."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code: int | None = status_code


class HoudinAccountError(HoudinError):
    """A refusal that concerns the account, not one artifact: rejected key, spent quota, daily cap, unreachable API."""
