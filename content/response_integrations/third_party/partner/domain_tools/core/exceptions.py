"""Custom exceptions for the DomainTools integration."""

from __future__ import annotations


class DomainToolsManagerError(Exception):
    """General exception for DomainTools manager operations."""


class DomainToolsLicenseError(DomainToolsManagerError):
    """Raised when a required product license is not available."""


class DomainToolsApiError(DomainToolsManagerError):
    """Raised for errors returned by the DomainTools API."""
