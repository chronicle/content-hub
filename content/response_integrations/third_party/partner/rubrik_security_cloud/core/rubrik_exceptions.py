from __future__ import annotations


class RubrikException(Exception):
    """
    Base exception class for all Rubrik Security Cloud integration errors.
    """

    pass


class InternalServerError(RubrikException):
    """Exception for server-side errors (5xx)."""

    pass


# Alias for backward compatibility (typo kept intentionally)
InternalSeverError = InternalServerError


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


class ConnectionTimeoutException(RubrikException):
    """
    Exception raised when the Rubrik endpoint is unreachable or times out
    (connection refused, DNS failure, connect/read timeout, invalid URL).
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


class TokenExpiredException(RubrikException):
    """Exception raised when a token cannot be refreshed."""

    pass


class InvalidValueException(RubrikException):
    """Exception for invalid enum or dropdown parameter values."""

    pass


class InvalidFormatException(RubrikException):
    """Exception for invalid format of parameter values."""

    pass


class AmbiguousFileMatchException(RubrikException):
    """Raised when more than one generated file matches the expected filename and
    was created after the action started, so the correct file cannot be
    determined with certainty."""

    pass
