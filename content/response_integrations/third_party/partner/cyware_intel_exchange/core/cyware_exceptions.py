from __future__ import annotations


class CywareException(Exception):
    """
    General Exception for Cyware integration
    """

    pass


class InvalidIntegerException(CywareException):
    """
    Exception for invalid integer parameters
    """

    pass


class RateLimitException(CywareException):
    """
    Exception for rate limit
    """

    pass


class UnauthorizedException(CywareException):
    """
    Exception for unauthorized access
    """

    pass


class InternalServerError(CywareException):
    """
    Internal Server Error
    """

    pass


class ItemNotFoundException(CywareException):
    """
    Exception for not found (404) errors
    """

    pass


class InvalidFormatException(CywareException):
    """Exception for invalid input formatting."""

    pass
