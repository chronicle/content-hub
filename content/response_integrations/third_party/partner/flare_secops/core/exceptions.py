"""Typed exceptions for Flare API interactions."""
from __future__ import annotations


class FlareException(Exception):
    """General exception for Flare manager operations."""


class FlareValidationException(FlareException):
    """Invalid configuration or request payload."""


class FlareBadRequestException(FlareException):
    """HTTP 400 from Flare."""


class FlareUnauthorizedException(FlareException):
    """HTTP 401 from Flare — credentials invalid or token expired."""


class FlareForbiddenException(FlareException):
    """HTTP 403 from Flare — insufficient permissions."""


class FlareNotFoundException(FlareException):
    """HTTP 404 from Flare."""


class FlareRateLimitException(FlareException):
    """HTTP 429 from Flare."""
