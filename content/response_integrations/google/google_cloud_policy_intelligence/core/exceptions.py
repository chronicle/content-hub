from __future__ import annotations
class GoogleCloudPolicyIntelligenceError(Exception):
    """General Exception for Google Cloud Policy Intelligence"""


class InsufficientResourcePermissionError(GoogleCloudPolicyIntelligenceError):
    """No permissions granted for Project Or Organization level"""


class ProjectNotFoundError(GoogleCloudPolicyIntelligenceError):
    """Project ID not found for requested API service"""


class MaximumRequestLimitError(GoogleCloudPolicyIntelligenceError):
    """Maximum requests sent in a given amount of time"""


class InvalidServiceAccountError(GoogleCloudPolicyIntelligenceError):
    """Service Account details are not correct"""
