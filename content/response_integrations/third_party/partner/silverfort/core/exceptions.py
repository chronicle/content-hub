"""Custom exceptions for Silverfort integration."""

from __future__ import annotations


class SilverfortError(Exception):
    """Base exception for Silverfort integration."""


class SilverfortConfigurationError(SilverfortError):
    """Exception raised when integration configuration is invalid or missing."""


class SilverfortAuthenticationError(SilverfortError):
    """Exception raised when authentication fails."""


class SilverfortHTTPError(SilverfortError):
    """Exception raised for HTTP errors."""

    def __init__(self, message: str, *args, status_code: int | None = None) -> None:
        """Initialize the exception.

        Args:
            message: Error message.
            *args: Additional positional arguments.
            status_code: HTTP status code.
        """
        super().__init__(message, *args)
        self.status_code = status_code


class SilverfortAPIError(SilverfortError):
    """Exception raised for API-specific errors."""

    def __init__(
        self,
        message: str,
        *args,
        error_code: str | None = None,
        details: dict | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Error message.
            *args: Additional positional arguments.
            error_code: Silverfort-specific error code.
            details: Additional error details.
        """
        super().__init__(message, *args)
        self.error_code = error_code
        self.details = details or {}


class SilverfortInvalidParameterError(SilverfortError):
    """Exception raised when action parameters are invalid."""


class SilverfortEntityNotFoundError(SilverfortError):
    """Exception raised when a requested entity is not found."""


class SilverfortCredentialsNotConfiguredError(SilverfortConfigurationError):
    """Exception raised when required API credentials are not configured."""

    def __init__(self, api_type: str) -> None:
        """Initialize the exception.

        Args:
            api_type: Type of API whose credentials are missing.
        """
        self.api_type = api_type
        super().__init__(
            f"{api_type} API credentials are not configured. "
            f"Please configure the {api_type} App User ID and {api_type} App User Secret "
            "in the integration settings."
        )
