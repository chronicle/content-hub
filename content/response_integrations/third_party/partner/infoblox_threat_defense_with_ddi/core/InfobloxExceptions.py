from __future__ import annotations


class InfobloxException(Exception):
    """
    Common Infoblox Exception
    """


class ItemNotFoundException(InfobloxException):
    """
    Exception for not found (404) errors, e.g., Custom List does not exist
    """


class RateLimitException(InfobloxException):
    """
    Exception for rate limit
    """


class InternalSeverError(InfobloxException):
    """
    Internal Server Error
    """


class InvalidIntegerException(InfobloxException):
    """
    Custom exception for invalid integer parameters.
    """
