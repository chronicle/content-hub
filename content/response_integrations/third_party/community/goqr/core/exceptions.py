from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


class GOQRError(Exception):
    """A custom exception for the QR Utilities integration."""

    pass


class GOQRHTTPError(GOQRError):
    """A custom exception for HTTP errors in the QR Utilities integration."""

    def __init__(self, message: str, status_code: int, *args: Any) -> None:
        super().__init__(message, *args)
        self.status_code = status_code


class InvalidRequestParametersError(GOQRError):
    """A custom exception for invalid request parameters."""

    pass
