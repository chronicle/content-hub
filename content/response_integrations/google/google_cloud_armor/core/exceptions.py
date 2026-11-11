from __future__ import annotations
class GoogleCloudArmorError(Exception):
    """Exceptions for Google Cloud Armor"""


class GoogleCloudArmorInvalidJsonError(Exception):
    """Exception in case of Invalid JSON"""


class GoogleCloudArmorStatusNotFoundError(GoogleCloudArmorError):
    """Exception in case of requested response not found."""


class GoogleCloudArmorValidationError(GoogleCloudArmorError):
    """Exception in case of invalid data provided."""


class GoogleCloudArmorPermissionsDeniedError(GoogleCloudArmorError):
    """Exception in case of permissions denied on your request."""


class GoogleCloudArmorRetryExceededError(GoogleCloudArmorError):
    """Exception in case of permissions denied on your request."""


class GoogleCloudArmorPolicyNotFoundError(GoogleCloudArmorError):
    """Exception in case of security policy not found."""


class GoogleCloudArmorInvalidRegionError(GoogleCloudArmorError):
    """Exception in case of region is invalid."""
