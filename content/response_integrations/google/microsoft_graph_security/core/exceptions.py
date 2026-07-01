from __future__ import annotations
class MicrosoftGraphSecurityFileNotFound(Exception):
    """File not found exception for microsoft graph security"""


class ActionParameterValidationError(Exception):
    """Generic error for parameters validation error inside action body"""


class MicrosoftGraphSecurityManagerError(Exception):
    """ General Exception for microsoft graph security manager"""


class IncidentNotFoundException(Exception):
    """Exception when Incident not found."""


class AlertNotFoundException(Exception):
    """Exception when Alert not found."""
