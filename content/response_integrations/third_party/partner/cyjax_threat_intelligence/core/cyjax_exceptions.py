from __future__ import annotations


class CyjaxException(Exception):
    """
    General Exception for Cyjax integration
    """

    pass


class InvalidIntegerException(CyjaxException):
    """
    Exception for invalid integer parameters
    """

    pass


class RateLimitException(CyjaxException):
    """
    Exception for rate limit
    """

    pass


class UnauthorizedException(CyjaxException):
    """
    Exception for unauthorized access
    """

    pass


class InternalServerError(CyjaxException):
    """
    Internal Server Error
    """

    pass


class ItemNotFoundException(CyjaxException):
    """
    Exception for not found (404) errors
    """

    pass
