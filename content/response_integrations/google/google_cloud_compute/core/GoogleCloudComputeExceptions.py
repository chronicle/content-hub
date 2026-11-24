from __future__ import annotations
class GoogleCloudComputeManagerError(Exception):
    """
    General Exception for Google Cloud Compute manager
    """


class GoogleCloudComputeAPILimitError(Exception):
    """
    API Limit Exception for Google Cloud Compute manager
    """


class GoogleCloudComputeResourceNameValidationError(Exception):
    """
    Resource Name Validation Exception for Google Cloud Compute manager
    """


class GoogleCloudComputeOperationError(Exception):
    """
    Operation Exception for Google Cloud Compute manager
    """


class GoogleCloudComputeValidationError(Exception):
    """
    Validation Exception for Google Cloud Compute manager
    """


class GoogleCloudComputeInvalidZone(Exception):
    """
    Invalid Zone Exception for Google Cloud Compute manager
    """


class GoogleCloudTransportException(Exception):
    """
    Transport Exception for Google Cloud Compute manager
    """


class GoogleCloudAuthenticationError(Exception):
    """
    Google Cloud Compute Authentication Error for Google Cloud Compute manager
    """


class GoogleCloudComputeInvalidInstanceID(Exception):
    """
    Google Cloud Compute Invalid Instance ID Error for Google Cloud Compute manager
    """


class GoogleCloudPolicyJSONError(Exception):
    """
    Google Cloud Compute Invalid IAM Policy JSON Error for Google Cloud Compute manager
    """


class GoogleCloudComputeLabelsValidationError(Exception):
    """
    Validation Exception for labels for Google Cloud Compute manager
    """


class GoogleCloudComputeTimeoutError(Exception):
    """
    Timeout Exception for Google Cloud Compute actions.
    """
