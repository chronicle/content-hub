from __future__ import annotations


class RubrikException(Exception):
    """
    Base exception class for all Rubrik Security Cloud integration errors.
    """

    pass


class ItemNotFoundException(RubrikException):
    """
    Exception raised when a requested resource is not found.
    """

    pass


class RateLimitException(RubrikException):
    """
    Exception raised when API rate limit is exceeded.
    """

    pass


class InternalSeverError(RubrikException):
    """
    Exception raised for internal server errors.
    """

    pass


class InvalidIntegerException(RubrikException):
    """
    Custom exception for invalid integer parameters.
    """

    pass


class GraphQLQueryException(RubrikException):
    """
    Exception raised when GraphQL query execution fails or returns errors.

    This exception is used for GraphQL-specific errors returned in the response.
    """

    pass


class UnauthorizedErrorException(RubrikException):
    """
    Exception raised for authentication and authorization failures (401 status code).
    """

    pass
