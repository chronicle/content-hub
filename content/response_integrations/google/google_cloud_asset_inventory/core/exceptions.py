from __future__ import annotations
class GoogleCloudAssetInventoryError(Exception):
    """General Exception for Google Cloud Asset Inventory"""


class InsufficientResourcePermissionError(GoogleCloudAssetInventoryError):
    """No permissions granted for Project Or Organization level"""


class ProjectOrOrganizationNotFoundError(GoogleCloudAssetInventoryError):
    """Project Or Organization Level/Id not found for requested API service"""


class MaximumRequestLimitError(GoogleCloudAssetInventoryError):
    """Maximum requests sent in a given amount of time"""


class InvalidServiceAccountError(GoogleCloudAssetInventoryError):
    """Service Account details are not correct"""
