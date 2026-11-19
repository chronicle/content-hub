from __future__ import annotations


class GoogleFormsManagerError(Exception):
    """General base exception for the Google Forms integration."""


class GoogleFormsValidationException(GoogleFormsManagerError):
    """Raised for data structure validation errors."""


class GoogleFormsAuthenticationError(GoogleFormsManagerError):
    """Raised for authentication-related errors."""


class InvalidJSONFormatException(GoogleFormsManagerError):
    """Raised for errors in parsing JSON responses."""


class InvalidParameterException(GoogleFormsManagerError):
    """Raised for invalid parameters provided to a method."""


class InvalidFormIdsException(GoogleFormsManagerError):
    """Raised for errors related to invalid form IDs."""
