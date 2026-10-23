"""Typed exceptions for Vega API interactions."""

from __future__ import annotations


class VegaException(Exception):
    """General exception for Vega manager operations."""


class VegaValidationException(VegaException):
    """Invalid configuration or request payload."""


class VegaBadRequestException(VegaException):
    """HTTP 400 from Vega."""


class VegaUnauthorizedException(VegaException):
    """HTTP 401 from Vega."""


class VegaForbiddenException(VegaException):
    """HTTP 403 from Vega."""


class VegaNotFoundException(VegaException):
    """HTTP 404 from Vega."""


class VegaRateLimitException(VegaException):
    """HTTP 429 after bounded retries."""


class VegaTimeoutException(VegaException):
    """Connect or read timeout."""
