from __future__ import annotations
class GoogleGKEValidationError(Exception):
    """
    General Exception for Google GKE validation errors.
    """


class GoogleGKEManagerError(Exception):
    """
    General Exception for Google Kubernetes Engine manager
    """


class GoogleCloudAuthenticationError(Exception):
    """
    General Exception for Google Cloud Authentication errors.
    """


class GoogleGKEServiceError(Exception):
    """
    General Exception for Google Kubernetes Engine service.
    """


class GoogleGKEManagerCriticalError(Exception):
    """
    Critical Exception for Google Kubernetes Engine manager
    """


class GoogleGKEProjectLookupError(GoogleGKEManagerCriticalError):
    """
    Project Lookup Exception for Google Kubernetes Engine manager
    """


class GoogleGKENotFoundError(GoogleGKEManagerError):
    """
    Not Found Exception for Google Kubernetes Engine manager
    """


class GoogleGKEInvalidRequestArgumentError(GoogleGKEManagerError):
    """
    Invalid Request Argument Exception for Google Kubernetes Engine manager
    """


class GoogleGKEInvalidZoneError(GoogleGKEInvalidRequestArgumentError):
    """
    Invalid Zone Exception for Google Kubernetes Engine manager
    """


class GoogleGKEInvalidClusterNameError(GoogleGKEInvalidRequestArgumentError):
    """
    Exception for Invalid Cluster Name for Google Kubernetes Engine manager
    """


class GoogleGKEInvalidNodePoolNameError(GoogleGKEInvalidRequestArgumentError):
    """
    Exception for Invalid Cluster Node Pool Name for Google Kubernetes Engine manager
    """


class GoogleGKEInvalidOperationNameError(GoogleGKEInvalidRequestArgumentError):
    """
    Exception for Invalid Operation Name for Google Kubernetes Engine manager
    """


class NegativeValueException(Exception):
    """
    Exception for negative value
    """


class NonPositiveValueException(Exception):
    """
    Exception for non positive value
    """


class InvalidJSONFormatException(Exception):
    """
    Exception for invalid JSON format
    """


class MissingParametersException(Exception):
    """
    Exception for missing parameters
    """
