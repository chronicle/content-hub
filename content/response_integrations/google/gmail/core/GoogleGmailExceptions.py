from __future__ import annotations
class InvalidJSONFormatException(Exception):
    """Invalid JSON format error."""


class GoogleCloudAuthenticationError(Exception):
    """General Exception for Google Cloud Authentication errors."""


class GoogleGmailValidationError(Exception):
    """General Exception for Google Gmail validation errors."""


class GoogleGmailManagerError(Exception):
    """General Exception for Google Gmail manager."""


class GoogleGmailServiceError(Exception):
    """General Exception for Google Gmail service."""


class GoogleGmailPermissionDeniedError(GoogleGmailManagerError):
    """Permission denied for Google Gmail manager."""


class GoogleGmailProjectLookupError(GoogleGmailPermissionDeniedError):
    """Project Lookup Exception for Google Gmail manager."""


class GoogleGmailNotFoundError(GoogleGmailManagerError):
    """Not Found Exception for Google Gmail manager."""


class GoogleGmailInvalidRequestArgumentError(GoogleGmailManagerError):
    """Invalid Request Argument Exception for Google Gmail manager."""


class GoogleGmailThrottlingOverloaded(GoogleGmailManagerError):
    """Throttling Exception for Google Gmail service."""
