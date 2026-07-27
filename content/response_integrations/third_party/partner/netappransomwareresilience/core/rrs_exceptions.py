"""Custom exceptions for NetApp Ransomware Resilience integration."""

from __future__ import annotations


class RrsException(Exception):
    """Base exception for all NetApp Ransomware Resilience errors."""


class RrsAuthenticationError(RrsException):
    """Raised when authentication fails (e.g. invalid credentials or token)."""


class RrsConnectionError(RrsException):
    """Raised when a network/connection error occurs reaching the RRS service."""


class RrsApiError(RrsException):
    """Raised when the RRS API returns a non-2xx HTTP error response."""


class RrsTimeoutError(RrsException):
    """Raised when a request to the RRS API times out."""


class RrsInvalidParameterError(RrsException):
    """Raised when required action parameters are missing or invalid."""


class RrsResponseParseError(RrsException):
    """Raised when the API response cannot be parsed (e.g. unexpected JSON structure)."""
