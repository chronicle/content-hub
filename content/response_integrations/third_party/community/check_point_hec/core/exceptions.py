class CheckPointHECIntegrationError(Exception):
    """General exception for Check Point HEC Integration."""


class CheckPointHECPermissionsError(CheckPointHECIntegrationError):
    """Exception for permission-related errors in Check Point HEC Integration."""
