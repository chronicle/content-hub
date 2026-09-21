from __future__ import annotations


class CensysException(Exception):
    """
    Base exception class for all Censys integration errors.
    """

    pass


class ItemNotFoundException(CensysException):
    """
    Exception raised when a requested resource is not found.
    """

    pass


class ForbiddenErrorException(CensysException):
    """
    Exception raised when the account does not have permission to access the
    requested resource (403 status code).
    """

    pass


class FeatureNotEnabledException(CensysException):
    """
    Exception raised when the requested feature is not enabled for the
    account's tier (409 status code).
    """

    pass


class RateLimitException(CensysException):
    """
    Exception raised when API rate limit is exceeded.
    """

    pass


class InternalServerError(CensysException):
    """
    Exception raised for internal server errors.
    """

    pass


class InvalidIntegerException(CensysException):
    """
    Exception raised when an invalid integer parameter is provided.
    """

    pass


class UnauthorizedErrorException(CensysException):
    """
    Exception raised for authentication and authorization failures (401 status code).
    """

    pass


class ValidationException(CensysException):
    """
    Exception raised when input validation fails.
    """

    pass


class PartialDataException(CensysException):
    """
    Exception raised when pagination fails mid-way but partial data was collected.
    This allows returning successfully fetched pages along with error information.
    """

    def __init__(self, message: str, collected_data: dict, error_details: dict) -> None:
        """
        Initialize PartialDataException with collected data and error context.

        Args:
            message: Human-readable error message
            collected_data: Dictionary containing successfully collected data
            error_details: Dictionary with error metadata (type, page, retries, etc.)
        """
        super().__init__(message)
        self.collected_data = collected_data
        self.error_details = error_details
