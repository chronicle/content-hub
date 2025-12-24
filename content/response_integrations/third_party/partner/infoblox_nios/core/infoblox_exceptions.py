from __future__ import annotations


class InfobloxException(Exception):
    """
    Common Infoblox Exception
    """

    pass


class ItemNotFoundException(InfobloxException):
    """
    Exception for not found (404) errors, e.g., Custom List does not exist
    """

    pass


class RateLimitException(InfobloxException):
    """
    Exception for rate limit
    """

    pass


class InternalSeverError(InfobloxException):
    """
    Internal Server Error
    """

    pass


class InvalidIntegerException(InfobloxException):
    """
    Custom exception for invalid integer parameters.
    """

    pass
